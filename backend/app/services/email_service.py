"""
Email fallback service using Resend.
Sends a branded HTML email when a reminder call is not answered.
"""

import logging
import resend
from app.config import get_settings

logger = logging.getLogger(__name__)


def send_reminder_email(to_email: str, title: str, message: str) -> bool:
    """Send a fallback reminder email via Resend. Returns True on success."""
    settings = get_settings()
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured — email fallback skipped.")
        return False

    resend.api_key = settings.RESEND_API_KEY

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#0f172a;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background-color:#1e293b;border-radius:16px;overflow:hidden;
                      border:1px solid #334155;max-width:560px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);
                       padding:32px;text-align:center;">
              <p style="margin:0 0 8px 0;font-size:32px;">📞</p>
              <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;
                         letter-spacing:-0.5px;">Missed Reminder</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <h2 style="margin:0 0 20px 0;color:#f1f5f9;font-size:18px;font-weight:600;">
                {title}
              </h2>
              <div style="background-color:#0f172a;border-radius:12px;padding:20px;
                          border-left:4px solid #6366f1;margin-bottom:24px;">
                <p style="margin:0;color:#cbd5e1;font-size:15px;line-height:1.7;">
                  {message}
                </p>
              </div>
              <p style="margin:0;color:#64748b;font-size:13px;line-height:1.6;">
                We tried calling you but couldn't reach you. This is your automatic
                fallback reminder from Smart Reminder System.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#0f172a;padding:16px 32px;text-align:center;
                       border-top:1px solid #1e293b;">
              <p style="margin:0;color:#475569;font-size:12px;">
                Smart Reminder System &middot; Sent automatically
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    try:
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to_email],
            "subject": f"Missed Reminder: {title}",
            "html": html_body,
        })
        logger.info("Email fallback sent to %s for reminder '%s'", to_email, title)
        return True
    except Exception as exc:
        logger.error("Email fallback failed for %s: %s", to_email, exc)
        return False
