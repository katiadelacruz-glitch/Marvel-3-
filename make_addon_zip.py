import os, zipfile

base_dir = "Marvel_LTI_History_Addon"
os.makedirs(base_dir, exist_ok=True)
os.makedirs(os.path.join(base_dir, "marvel_addons", "templates"), exist_ok=True)

# requirements.addon.txt
with open(os.path.join(base_dir, "requirements.addon.txt"), "w") as f:
    f.write("PyLTI1p3>=2.0.5\nAuthlib>=1.3.1\nSQLAlchemy>=2.0.30\n")

# settings.sample.py
with open(os.path.join(base_dir, "settings.sample.py"), "w") as f:
    f.write("""\
PLATFORM_ISSUER = "https://amathuba.uct.ac.za/"
CLIENT_ID = "REPLACE_WITH_CLIENT_ID_FROM_AMATHUBA"
DEPLOYMENT_ID = "REPLACE_WITH_DEPLOYMENT_ID"

OIDC_AUTH_ENDPOINT = "https://YOUR_BRIGHTSPACE/oidc/auth"
OIDC_TOKEN_ENDPOINT = "https://YOUR_BRIGHTSPACE/auth/token"
PLATFORM_JWKS_URL = "https://YOUR_BRIGHTSPACE/.well-known/jwks.json"

TOOL_JWKS_URL = "https://YOUR_TOOL_DOMAIN/lti/jwks"
TOOL_REDIRECT_URI = "https://YOUR_TOOL_DOMAIN/lti/launch"
TOOL_INITIATE_LOGIN_URI = "https://YOUR_TOOL_DOMAIN/lti/login"

TOOL_PRIVATE_KEY_PEM = '''-----BEGIN RSA PRIVATE KEY-----
REPLACE_WITH_YOUR_PRIVATE_KEY_PEM
-----END RSA PRIVATE KEY-----'''
""")

# models.py
models_code = """\
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, scoped_session
from datetime import datetime
import os

Base = declarative_base()
DB_URL = os.getenv("DATABASE_URL", "sqlite:///marvel_chat.db")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    lms_user_id = Column(String(128), index=True)
    name = Column(String(256))
    role = Column(String(64))
    messages = relationship("Message", back_populates="user")

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    lms_course_id = Column(String(128), index=True)
    title = Column(String(256))
    messages = relationship("Message", back_populates="course")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    role = Column(String(16))
    content = Column(Text)
    ts = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="messages")
    course = relationship("Course", back_populates="messages")

def init_db(app):
    Base.metadata.create_all(engine)
    @app.teardown_appcontext
    def remove_session(_=None):
        SessionLocal.remove()

def db_session():
    return SessionLocal
"""
with open(os.path.join(base_dir, "marvel_addons", "models.py"), "w") as f:
    f.write(models_code)

# history_hooks.py
history_hooks = """\
from flask import session
from .models import db_session, User, Course, Message

def current_user_and_course():
    lms_user_id = session.get("lti_user_id", "anon")
    lms_course_id = session.get("lti_course_id", "general")
    name = session.get("lti_user_name", "Student")
    role = session.get("lti_user_role", "Learner")

    db = db_session()
    user = db.query(User).filter_by(lms_user_id=lms_user_id).first()
    if not user:
        user = User(lms_user_id=lms_user_id, name=name, role=role)
        db.add(user); db.commit()

    course = db.query(Course).filter_by(lms_course_id=lms_course_id).first()
    if not course:
        course = Course(lms_course_id=lms_course_id, title="Course")
        db.add(course); db.commit()
    return user, course, db

def save_interaction(sess, user_text, assistant_text):
    user, course, db = current_user_and_course()
    db.add_all([
        Message(user_id=user.id, course_id=course.id, role="user", content=user_text),
        Message(user_id=user.id, course_id=course.id, role="assistant", content=assistant_text),
    ])
    db.commit()
"""
with open(os.path.join(base_dir, "marvel_addons", "history_hooks.py"), "w") as f:
    f.write(history_hooks)

# lti_blueprint.py
lti_blueprint = """\
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
"""
with open(os.path.join(base_dir, "marvel_addons", "lti_blueprint.py"), "w") as f:
    f.write(lti_blueprint)

# lti_launch.html
with open(os.path.join(base_dir, "marvel_addons", "templates", "lti_launch.html"), "w") as f:
    f.write("<!doctype html><html><body><h2>Hello from Amathuba LTI Launch!</h2></body></html>")

# create zip
zip_name = "Marvel_LTI_History_Addon.zip"
with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(base_dir):
        for file in files:
            filepath = os.path.join(root, file)
            zf.write(filepath, os.path.relpath(filepath, base_dir))

print(f"Created: {zip_name}")
