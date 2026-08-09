import hashlib
import logging
import secrets
from datetime import timedelta

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

CONTACT_CODE_TTL = timedelta(minutes=10)
CONTACT_RESEND_COOLDOWN = timedelta(minutes=1)
MAX_CONTACT_VERIFICATION_ATTEMPTS = 5


class MailgunDeliveryError(Exception):
    """Raised when Mailgun rejects or cannot receive a verification email."""


def create_contact_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def normalize_contact_email(email: str) -> str:
    return email.strip().lower()


def digest_contact_verification_code(email: str, code: str) -> str:
    payload = (
        f"{normalize_contact_email(email)}:{code.strip()}:"
        f"{settings.CONTACT_VERIFICATION_SECRET}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def send_contact_verification_code(email: str, code: str) -> None:
    api_key = settings.MAILGUN_API_KEY
    domain = settings.MAILGUN_DOMAIN
    from_email = settings.MAILGUN_FROM_EMAIL
    api_base = settings.MAILGUN_API_BASE.rstrip("/")

    if not api_key or not domain or not from_email:
        raise ImproperlyConfigured("Email verification is not configured.")

    try:
        response = requests.post(
            f"{api_base}/v3/{domain}/messages",
            auth=("api", api_key),
            data={
                "from": from_email,
                "to": email,
                "subject": f"{code} is your Blueskies verification code",
                "text": (
                    "Your Blueskies early access verification code is "
                    f"{code}. It expires in 10 minutes. If you did not "
                    "request this, you can ignore this email."
                ),
            },
            timeout=settings.MAILGUN_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning("Mailgun request failed before receiving a response: %s", exc)
        raise MailgunDeliveryError(
            "We could not send the verification email. Please try again."
        ) from exc

    if not response.ok:
        logger.warning(
            "Mailgun request failed with status %s: %s",
            response.status_code,
            response.text,
        )
        raise MailgunDeliveryError(
            "We could not send the verification email. Please try again."
        )
