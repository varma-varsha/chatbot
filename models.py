from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

# Initialize SQLAlchemy without app
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    import os
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "OneLearn", "instance", "users.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize db with app
    db.init_app(app)

    return app


app = create_app()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class CourseProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_language = db.Column(db.String(50), nullable=False)
    chapters_completed = db.Column(db.JSON, default=lambda: [])
    last_accessed_chapter = db.Column(db.Integer, default=1)
    progress_percentage = db.Column(db.Float, default=0.0)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='course_progress')

    def __repr__(self):
        return f'<CourseProgress {self.user_id} - {self.course_language}>'