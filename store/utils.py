# utils.py
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from typing import Any


def send_verification_email(user: Any) -> None:
    """
    Generates a token and sends a routing path redirecting
    directly to the customer's User Interface (Frontend).
    """
    # 1. Transform the User ID into a web-safe base64 string snippet
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # 2. Compute the cryptographic hash token
    token = default_token_generator.make_token(user)

    # 3. ◄ CHANGE HERE: Point directly to your Frontend Web URL path router!
    # In production, swap 'localhost:3000' with your live domain (e.g., https://myfrontend.com)
    FRONTEND_DOMAIN = "http://localhost:3000"
    frontend_verification_url = (
        f"{FRONTEND_DOMAIN}/verify-account?uid={uid}&token={token}"
    )

    subject = "Verify Your Email Address"
    message = (
        f"Hi {user.name or user.username},\n\n"
        f"Thank you for registering! Please click the secure link below to verify your account:\n\n"
        f"{frontend_verification_url}\n\n"
        f"If you did not create an account, please disregard this email."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def send_password_reset_email(user: Any) -> None:
    """
    Generates a one-time reset token and emails a secure
    password reset link directly to the user's inbox.
    """
    # 1. Transform the User ID into a web-safe base64 string
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # 2. Compute the cryptographic one-time token
    token = default_token_generator.make_token(user)

    # 3. Point to your frontend reset page
    FRONTEND_DOMAIN = "http://localhost:3000"
    frontend_reset_url = f"{FRONTEND_DOMAIN}/reset-password?uid={uid}&token={token}"

    subject = "Reset Your Password"
    message = (
        f"Hi {user.name or user.username},\n\n"
        f"We received a request to reset your password. "
        f"Click the link below to set a new password:\n\n"
        f"{frontend_reset_url}\n\n"
        f"This link will expire after 24 hours.\n\n"
        f"If you did not request a password reset, please ignore this email."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
