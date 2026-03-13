from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DateField,
    HiddenField,
    PasswordField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, NumberRange, Optional


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    password_confirmation = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords do not match.")],
    )
    submit = SubmitField("Create Account")


class ProfileForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone", validators=[DataRequired()])
    address = TextAreaField("Address", validators=[DataRequired()])
    submit = SubmitField("Update Profile")


class PasswordUpdateForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    password = PasswordField("New Password", validators=[DataRequired()])
    password_confirmation = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("password", message="New passwords do not match.")],
    )
    submit = SubmitField("Update Password")


class OrderConfirmForm(FlaskForm):
    customer_name = StringField("Customer Name", validators=[Optional()])
    email = StringField("Email", validators=[Optional(), Email()])
    phone = StringField("Phone", validators=[Optional()])
    address = TextAreaField("Address", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Place Order")


class FeedbackForm(FlaskForm):
    order_id = HiddenField("Order ID", validators=[Optional()])
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone", validators=[DataRequired()])
    message = TextAreaField("Feedback", validators=[DataRequired()])
    promotion = RadioField(
        "Do you want promotions?",
        choices=[("Y", "Yes"), ("N", "No")],
        validators=[DataRequired()],
    )
    sms = BooleanField("SMS")
    whatsapp = BooleanField("WhatsApp")
    emailch = BooleanField("Email")
    submit = SubmitField("Send Feedback")


class AdminProductForm(FlaskForm):
    name = StringField("Accessory Name", validators=[DataRequired()])
    category = SelectField("Category", choices=[], validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional()])
    price = StringField("Price", validators=[DataRequired()])
    image_file = FileField(
        "Image File",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp", "gif"], "Invalid image type.")],
    )
    is_featured = BooleanField("Mark as Featured Accessory")
    submit = SubmitField("Add Accessory")


class AdminDateRangeForm(FlaskForm):
    from_date = DateField("From", format="%Y-%m-%d", validators=[DataRequired()])
    to_date = DateField("To", format="%Y-%m-%d", validators=[DataRequired()])
    submit = SubmitField("Generate")


class OrderStatusForm(FlaskForm):
    status = SelectField("Status", choices=[], validators=[DataRequired()])
    next = HiddenField("Next", validators=[Optional()])
    submit = SubmitField("Update")
