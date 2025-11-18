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
