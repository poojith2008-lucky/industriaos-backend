import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from app.core.config import settings


def send_email(
    subject: str,
    body: str,
    recipients: List[str],
    attachment_path: Optional[str] = None,
    is_html: bool = False,
) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"]    = settings.MAIL_FROM
        msg["To"]      = ", ".join(recipients)
        msg["Subject"] = subject

        content_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, content_type))

        # ── Attach file if provided ──────────────────────────
        if attachment_path and os.path.exists(attachment_path):
            filename = os.path.basename(attachment_path)
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)

        # ── Send via SMTP ────────────────────────────────────
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            if settings.MAIL_STARTTLS:
                server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.sendmail(settings.MAIL_FROM, recipients, msg.as_string())

        return True

    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def send_salary_slip(
    employee_email: str,
    employee_name: str,
    month_year: str,
    base: float,
    bonus: float,
    deductions: float,
    net: float,
    qr_code_path: Optional[str] = None,
) -> bool:
    subject = f"Salary Slip — {month_year} | IndustriaOS"
    body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto;">
      <div style="background:#080B14;padding:24px;border-radius:12px;color:#fff;margin-bottom:20px;">
        <h2 style="margin:0;color:#FF6B35;">IndustriaOS</h2>
        <p style="margin:4px 0 0;color:rgba(255,255,255,0.5);font-size:13px;">Salary Slip</p>
      </div>
      <p>Dear <strong>{employee_name}</strong>,</p>
      <p>Your salary for <strong>{month_year}</strong> has been processed.</p>
      <table style="width:100%;border-collapse:collapse;margin:20px 0;">
        <tr style="background:#f5f5f5;">
          <td style="padding:10px 14px;border:1px solid #ddd;">Base Salary</td>
          <td style="padding:10px 14px;border:1px solid #ddd;text-align:right;">₹{base:,.0f}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;border:1px solid #ddd;">Bonus</td>
          <td style="padding:10px 14px;border:1px solid #ddd;text-align:right;color:green;">+₹{bonus:,.0f}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;border:1px solid #ddd;">Deductions</td>
          <td style="padding:10px 14px;border:1px solid #ddd;text-align:right;color:red;">-₹{deductions:,.0f}</td>
        </tr>
        <tr style="background:#080B14;color:#fff;">
          <td style="padding:12px 14px;border:1px solid #333;font-weight:bold;">Net Salary</td>
          <td style="padding:12px 14px;border:1px solid #333;text-align:right;font-weight:bold;color:#FF6B35;">₹{net:,.0f}</td>
        </tr>
      </table>
      <p style="color:#888;font-size:12px;">This is an automated email from IndustriaOS.</p>
    </body></html>
    """
    return send_email(
        subject=subject,
        body=body,
        recipients=[employee_email],
        attachment_path=qr_code_path,
        is_html=True
    )


def send_bulk_announcement(
    subject: str,
    body: str,
    recipients: List[str],
    attachment_path: Optional[str] = None,
) -> dict:
    success, failed = 0, 0
    for email in recipients:
        ok = send_email(subject, body, [email], attachment_path, is_html=True)
        if ok: success += 1
        else:  failed  += 1
    return {"success": success, "failed": failed, "total": len(recipients)}