"""Razorpay gateway integration helpers for creating and verifying course orders."""

from decimal import Decimal, ROUND_HALF_UP
import razorpay
from django.conf import settings


class RazorpayConfigurationError(Exception):
    """Raised when Razorpay API credentials are missing or incomplete."""


def get_razorpay_credentials() -> tuple[str, str]:
    """Return configured (key_id, key_secret) or raise RazorpayConfigurationError."""
    key_id = (getattr(settings, 'RAZORPAY_KEY_ID', '') or '').strip()
    key_secret = (getattr(settings, 'RAZORPAY_KEY_SECRET', '') or '').strip()
    if not key_id or not key_secret:
        raise RazorpayConfigurationError(
            "Razorpay API keys are not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env."
        )
    return key_id, key_secret


def get_razorpay_client() -> razorpay.Client:
    """Create an authenticated Razorpay SDK client."""
    key_id, key_secret = get_razorpay_credentials()
    return razorpay.Client(auth=(key_id, key_secret))


def amount_to_paise(amount_inr: Decimal) -> int:
    """Convert an INR Decimal amount cleanly to integer paise."""
    return int((amount_inr * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def create_razorpay_order(amount_paise: int, receipt: str, notes: dict | None = None) -> dict:
    """Create a Razorpay order via the Orders API and return the response dictionary."""
    client = get_razorpay_client()
    payload = {
        'amount': amount_paise,
        'currency': 'INR',
        'receipt': receipt[:40],
        'payment_capture': 1,
    }
    if notes:
        payload['notes'] = notes
    return client.order.create(payload)


def verify_razorpay_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """Verify the Razorpay Checkout HMAC-SHA256 payment signature."""
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
