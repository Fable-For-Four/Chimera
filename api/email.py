import html
import logging
import os

import resend

logger = logging.getLogger("chimera.email")

DEFAULT_FROM = "onboarding@resend.dev"


def send_verification_email(to, name, link):
    key = os.environ.get("RESEND_API_KEY", "")
    if not key:
        logger.warning("RESEND_API_KEY is not set. Verification link for %s: %s", to, link)
        return
    text = (
        f"Hi {name},\n\n"
        f"Confirm your email for Chimera by opening this link:\n{link}\n\n"
        "This link works for 30 minutes.\n"
    )
    safe_link = html.escape(link, quote=True)
    body = (
        f"<p>Hi {html.escape(name)},</p>"
        "<p>Confirm your email for Chimera by opening this link:</p>"
        f'<p><a href="{safe_link}">{safe_link}</a></p>'
        "<p>This link works for 30 minutes.</p>"
    )
    resend.api_key = key
    try:
        resend.Emails.send(
            {
                "from": os.environ.get("EMAIL_FROM") or DEFAULT_FROM,
                "to": [to],
                "subject": "Confirm your email",
                "text": text,
                "html": body,
            }
        )
    except Exception as exc:
        # Only the type: Resend's message could echo the link or token back.
        logger.error("Could not send the verification email: %s", type(exc).__name__)
