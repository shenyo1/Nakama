"""Email sending helper.

In production we expect either:
  - ``SMTP_HOST`` + ``SMTP_PORT`` + ``SMTP_USER`` + ``SMTP_PASS`` to send
    via SMTP (Mailgun, SendGrid, Postmark, Gmail, etc.).
  - ``SMTP_DISABLED=1`` to skip sending entirely and return the link in the
    API response (useful for self-hosted personal installs where the user
    is the only one who would receive the email).

If SMTP is configured but the connection fails, we fall through to the
``SMTP_DISABLED`` path so the request doesn't 500 — losing an email is
preferable to losing a password-reset attempt.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


def is_disabled() -> bool:
    """True when SMTP is not configured or explicitly disabled.

    Used by the auth endpoints to decide whether to send a real email or
    return the reset/confirmation link in the response payload so the user
    (or the dev) can copy it manually.
    """
    if os.getenv("SMTP_DISABLED", "").strip() in ("1", "true", "yes"):
        return True
    if not os.getenv("SMTP_HOST"):
        return True
    return False


def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
) -> bool:
    """Send a plain-text (or HTML) email via SMTP.

    Returns ``True`` on success, ``False`` on any failure. Never raises —
    callers should treat ``False`` as a soft failure and fall back to
    returning the link in the API response.
    """
    if is_disabled():
        return False

    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    sender = os.getenv("SMTP_FROM", user or "noreply@nakama.local")
    use_tls = os.getenv("SMTP_TLS", "1") not in ("0", "false", "no")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            if use_tls:
                smtp.starttls()
                smtp.ehlo()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        logger.warning("smtp send failed: %s", exc)
        return False
