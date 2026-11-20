"""
OTP Service for CourseSphere — Forgot Password Flow
----------------------------------------------------
Generates a 6-digit OTP, stores it in the Django session,
and sends it via Django's email backend (Gmail SMTP or console).
"""

import random
import time

from django.core.mail import send_mail
from django.conf import settings


OTP_EXPIRY_SECONDS = 600  # 10 minutes


def generate_otp() -> str:
    """Return a zero-padded 6-digit OTP string."""
    return f"{random.randint(0, 999999):06d}"


def send_otp(request, email: str, role: str = "user") -> bool:
    """
    Generate an OTP, save it in the session, and email it to `email`.
    `role` is used only for the email subject line ('Student' or 'Instructor').
    Returns True if the email was sent without raising an exception.
    """
    otp = generate_otp()
    request.session["otp_code"] = otp
    request.session["otp_email"] = email.lower().strip()
    request.session["otp_expires"] = time.time() + OTP_EXPIRY_SECONDS
    request.session["otp_role"] = role
    request.session.modified = True

    subject = f"CourseSphere — Your {role} Password Reset OTP"
    message = (
        f"Hello,\n\n"
        f"Your one-time password (OTP) for resetting your CourseSphere {role} account password is:\n\n"
        f"    {otp}\n\n"
        f"This OTP is valid for 10 minutes. Do not share it with anyone.\n\n"
        f"If you did not request a password reset, please ignore this email.\n\n"
        f"— CourseSphere Team"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        # Log to console so dev can still see the OTP
        print(f"\n[CourseSphere OTP] Could not send email: {exc}")
        print(f"[CourseSphere OTP] OTP for {email} → {otp}\n")
        return False


def verify_otp(request, otp_input: str) -> tuple[bool, str]:
    """
    Verify the OTP entered by the user against the session.
    Returns (True, "ok") on success or (False, reason_string) on failure.
    """
    stored_otp = request.session.get("otp_code")
    stored_email = request.session.get("otp_email")
    expires_at = request.session.get("otp_expires")

    if not stored_otp or not stored_email or not expires_at:
        return False, "No OTP session found. Please request a new OTP."

    if time.time() > expires_at:
        _clear_otp_session(request)
        return False, "OTP has expired. Please request a new one."

    if otp_input.strip() != stored_otp:
        return False, "Invalid OTP. Please try again."

    # Mark OTP as verified (keeps email in session for password-reset step)
    request.session["otp_verified"] = True
    request.session.modified = True
    return True, "ok"


def clear_otp_session(request):
    """Remove all OTP-related keys from the session after a successful reset."""
    _clear_otp_session(request)


def _clear_otp_session(request):
    for key in ("otp_code", "otp_email", "otp_expires", "otp_role", "otp_verified"):
        request.session.pop(key, None)
    request.session.modified = True
