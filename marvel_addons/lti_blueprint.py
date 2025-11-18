from flask import Blueprint, request, session, render_template, jsonify
from pylti1p3.tool_config import ToolConfJsonFile
from pylti1p3.flask import FlaskOIDCLogin, FlaskMessageLaunch, FlaskRequest
try:
    import settings
except ImportError:
    import settings_sample as settings

lti_bp = Blueprint("lti", __name__, template_folder="templates")

def _get_tool_conf():
    conf = {
        "iss": {
            settings.PLATFORM_ISSUER: {
                "client_id": settings.CLIENT_ID,
                "auth_login_url": settings.OIDC_AUTH_ENDPOINT,
                "auth_token_url": settings.OIDC_TOKEN_ENDPOINT,
                "key_set_url": settings.PLATFORM_JWKS_URL,
                "aud": settings.CLIENT_ID,
                "deployment_ids": [settings.DEPLOYMENT_ID]
            }
        }
    }
    return ToolConfJsonFile(conf)

@lti_bp.route("/login", methods=["GET"])
def login():
    tool_conf = _get_tool_conf()
    oidc_login = FlaskOIDCLogin(FlaskRequest(), tool_conf)
    return oidc_login.redirect(settings.TOOL_REDIRECT_URI, request.args)

@lti_bp.route("/launch", methods=["POST"])
def launch():
    tool_conf = _get_tool_conf()
    req = FlaskRequest()
    launch = FlaskMessageLaunch(req, tool_conf).validate_registration()
    launch_data = launch.get_launch_data()
    session["lti_user_id"] = launch_data.get("sub")
    session["lti_user_name"] = launch_data.get("name") or "Student"
    session["lti_course_id"] = launch_data.get("https://purl.imsglobal.org/spec/lti/claim/context", {}).get("id", "course")
    roles = launch_data.get("https://purl.imsglobal.org/spec/lti/claim/roles", [])
    session["lti_user_role"] = "Instructor" if any("Instructor" in r for r in roles) else "Learner"
    return render_template("lti_launch.html", user=session.get("lti_user_name"))

@lti_bp.route("/jwks", methods=["GET"])
def jwks():
    return jsonify({"keys": []})

@lti_bp.route("/history/me", methods=["GET"])
def my_history():
    from .models import db_session, User, Message
    uid = session.get("lti_user_id", "anon")
    db = db_session()
    user = db.query(User).filter_by(lms_user_id=uid).first()
    if not user:
        return jsonify([])
    msgs = db.query(Message).filter_by(user_id=user.id).order_by(Message.ts.desc()).limit(50).all()
    return jsonify([{"role": m.role, "content": m.content, "ts": m.ts.isoformat()} for m in msgs])

@lti_bp.route("/history/course", methods=["GET"])
def course_history():
    if session.get("lti_user_role") != "Instructor":
        return jsonify({"error": "Instructor only"}), 403
    from .models import db_session, Course, Message
    cid = session.get("lti_course_id", "course")
    db = db_session()
    course = db.query(Course).filter_by(lms_course_id=cid).first()
    if not course:
        return jsonify([])
    msgs = db.query(Message).filter_by(course_id=course.id).order_by(Message.ts.desc()).limit(100).all()
    return jsonify([{"role": m.role, "content": m.content, "ts": m.ts.isoformat()} for m in msgs])
