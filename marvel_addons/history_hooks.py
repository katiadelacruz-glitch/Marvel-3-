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
