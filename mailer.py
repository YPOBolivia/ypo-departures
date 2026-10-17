"""Sends email through a Google Apps Script web app that runs inside events@ypobolivia.com.

Render's free plan blocks SMTP, so the server calls the script over HTTPS instead.
The script checks a shared secret and sends with GmailApp as events@.
"""
import os
import httpx


class MailError(Exception):
    pass


def send(to: list[str], subject: str, html: str, text: str) -> None:
    url = os.environ.get("MAIL_WEBHOOK_URL")
    secret = os.environ.get("MAIL_SECRET")
    if not url or not secret:
        raise MailError("Email sending is not configured yet (MAIL_WEBHOOK_URL / MAIL_SECRET).")
    payload = {"secret": secret, "to": to, "subject": subject, "html": html, "text": text}
    try:
        r = httpx.post(url, json=payload, follow_redirects=True, timeout=45)
    except httpx.HTTPError as ex:
        raise MailError(f"Could not reach the sending script: {ex}") from ex
    try:
        data = r.json()
    except ValueError:
        raise MailError(f"The sending script answered unexpectedly (HTTP {r.status_code}).")
    if not data.get("ok"):
        raise MailError(f"The sending script refused: {data.get('error') or 'unknown error'}")
