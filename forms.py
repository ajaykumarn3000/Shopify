from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField
from wtforms.validators import DataRequired


class RegisterFormEmail(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])


class RegisterFormOTP(FlaskForm):
    # otp1 = StringField(validators=[DataRequired()])
    # otp2 = StringField(validators=[DataRequired()])
    # otp3 = StringField(validators=[DataRequired()])
    # otp4 = StringField(validators=[DataRequired()])
    # otp5 = StringField(validators=[DataRequired()])
    # otp6 = StringField(validators=[DataRequired()])
    otp = StringField(validators=[DataRequired()])


class RegisterFormPassword(FlaskForm):
    name = StringField(validators=[DataRequired()])
    password = PasswordField(validators=[DataRequired()])



class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
