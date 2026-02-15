from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=4, max=80, message="Username must be between 4 and 80 characters")
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message="Invalid email address")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please use a different email.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message="Invalid email address")
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')