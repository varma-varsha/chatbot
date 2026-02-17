from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
import os

# Initialize SQLAlchemy
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key_here'

    basedir = os.path.abspath(os.path.dirname(__file__))

    app.config['SQLALCHEMY_DATABASE_URI'] = \
        f'sqlite:///{os.path.join(app.instance_path, "users.db")}'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    return app


app = create_app()


# =============================
# User Model
# =============================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='customer')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# =============================
# Course Model
# =============================
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🔥 FIXED HERE
    chapters = db.relationship(
        'Chapter',
        backref='course',
        cascade='all, delete-orphan'
    )


# =============================
# Chapter Model
# =============================
class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(
        db.Integer,
        db.ForeignKey('course.id', ondelete='CASCADE'),
        nullable=False
    )
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    sample_code = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)


# =============================
# Course Progress Model
# =============================
class CourseProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )

    course_language = db.Column(db.String(50), nullable=False)
    chapters_completed = db.Column(db.JSON, default=lambda: [])
    last_accessed_chapter = db.Column(db.Integer, default=1)
    progress_percentage = db.Column(db.Float, default=0.0)

    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = db.relationship('User', backref='course_progress')

    def __repr__(self):
        return f'<CourseProgress {self.user_id} - {self.course_language}>'
