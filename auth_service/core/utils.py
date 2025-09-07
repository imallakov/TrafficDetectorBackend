import os
import random

from django.conf import settings
from django.core.mail import EmailMessage

from .models import OTP


def generate_otp(user, purpose):
    otp_code = str(random.randint(100000, 999999))
    otp = OTP.objects.create(user=user, otp=otp_code, purpose=purpose)

    # Send email
    # subject = "Your One-Time Password"
    message = ''
    if purpose == 'password_reset':
        message = (
            f"Ваш одно разовый пароль для сброса пароля на сайте TEST: <b>{otp_code}</b><br>"
            "Он будет действовать 15 минут."
        )
    elif purpose == 'email_verification':
        message = (
            f"Ваш одноразовый пароль для подтверждения почты на сайте TEST: <b>{otp_code}</b><br>"
            "Он будет действовать 15 минут."
        )
    send_custom_email(user.email, purpose, message)

    return otp


def send_custom_email(to_email: str, theme, message):
    """
    Sends an email with a specified theme and message (console output only).
    :param to_email: Recipient email address
    :param theme: Theme of the email
    :param message: Message content
    """
    subjects = {
        "email_verification": "TEST - Подтвердите вашу почту",
        "password_reset": "TEST - Сброс пароля",
    }
    subject = subjects.get(theme, "Уведомление с сайта TEST")

    # Create simple text email
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email]
    )

    # Send email (will be printed to console due to EMAIL_BACKEND setting)
    email.send()
