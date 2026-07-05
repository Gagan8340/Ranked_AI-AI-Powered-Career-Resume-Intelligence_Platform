import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import make_msgid, formatdate

from config import (
    APP_BASE_URL,
    EMAIL_FROM,
    TOKEN_EXPIRY_HOURS,
    PASSWORD_RESET_EXPIRY_HOURS,
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_USE_TLS
)

def test_email_connection():
    """Test SMTP connection on startup."""
    try:
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        if MAIL_USE_TLS:
            server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.quit()
        logging.info("Gmail SMTP connection successful")
        return True
    except Exception as e:
        logging.error(f"SMTP authentication failed: {str(e)}")
        return False

def _send_email(to_email: str, subject: str, html_content: str) -> dict:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="ranked1ai.com")

        part = MIMEText(html_content, "html")
        msg.attach(part)

        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        if MAIL_USE_TLS:
            server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, to_email, msg.as_string())
        server.quit()
        return {"success": True}
    except Exception as e:
        logging.error(f"Email delivery failed: {str(e)}")
        return {"success": False, "error": "Email delivery failed"}

def send_verification_email(recipient_email: str, recipient_name: str, verification_token: str) -> dict:
    url = f"{APP_BASE_URL}/auth/verify-email/{verification_token}"
    html_content = f"""
    <div style="background-color: #0f172a; padding: 40px 20px; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #cbd5e1;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155;">
            <div style="background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); padding: 30px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 1px;">AI Career Platform</h1>
            </div>
            <div style="padding: 40px 30px;">
                <h2 style="color: #f8fafc; margin-top: 0; font-size: 20px;">Welcome aboard, {recipient_name}!</h2>
                <p style="font-size: 16px; line-height: 1.6; color: #94a3b8;">
                    Thank you for joining our platform. We're thrilled to have you here. Before you can start using our AI-powered career tools, we just need to verify your email address.
                </p>
                <div style="text-align: center; margin: 40px 0;">
                    <a href="{url}" style="background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 16px; display: inline-block; box-shadow: 0 4px 14px rgba(139, 92, 246, 0.4);">Verify Email Address</a>
                </div>
                <p style="font-size: 14px; color: #64748b; margin-bottom: 0;">
                    This link will securely expire in {TOKEN_EXPIRY_HOURS} hours. If you did not create this account, you can safely ignore this email.
                </p>
            </div>
            <div style="background-color: #0f172a; padding: 20px; text-align: center; border-top: 1px solid #334155;">
                <p style="margin: 0; font-size: 12px; color: #475569;">&copy; 2026 Ranked1AI Team. All rights reserved.</p>
            </div>
        </div>
    </div>
    """
    result = _send_email(recipient_email, "Verify Your Email Address", html_content)
    if result["success"]:
        logging.info(f"Verification email sent to {recipient_email}")
    return result

def send_password_reset_email(recipient_email: str, recipient_name: str, reset_token: str) -> dict:
    url = f"{APP_BASE_URL}/auth/reset-password/{reset_token}"
    html_content = f"""
    <div style="background-color: #0f172a; padding: 40px 20px; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #cbd5e1;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155;">
            <div style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); padding: 30px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 1px;">Password Reset</h1>
            </div>
            <div style="padding: 40px 30px;">
                <h2 style="color: #f8fafc; margin-top: 0; font-size: 20px;">Hello {recipient_name},</h2>
                <p style="font-size: 16px; line-height: 1.6; color: #94a3b8;">
                    We received a request to reset your password. If you didn't make this request, you can safely ignore this email and your password will remain the same.
                </p>
                <div style="text-align: center; margin: 40px 0;">
                    <a href="{url}" style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 16px; display: inline-block; box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);">Reset My Password</a>
                </div>
                <p style="font-size: 14px; color: #64748b; margin-bottom: 0;">
                    This link will securely expire in {PASSWORD_RESET_EXPIRY_HOURS} hour{'s' if PASSWORD_RESET_EXPIRY_HOURS != 1 else ''}.
                </p>
            </div>
            <div style="background-color: #0f172a; padding: 20px; text-align: center; border-top: 1px solid #334155;">
                <p style="margin: 0; font-size: 12px; color: #475569;">&copy; 2026 Ranked1AI Team. All rights reserved.</p>
            </div>
        </div>
    </div>
    """
    result = _send_email(recipient_email, "Reset Your Password", html_content)
    if result["success"]:
        logging.info(f"Password reset email sent to {recipient_email}")
    return result

def send_welcome_email(recipient_email: str, recipient_name: str) -> dict:
    html_content = f"""
    <div style="background-color: #0f172a; padding: 40px 20px; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #cbd5e1;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155;">
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 1px;">Email Verified!</h1>
            </div>
            <div style="padding: 40px 30px;">
                <h2 style="color: #f8fafc; margin-top: 0; font-size: 20px;">Welcome to Ranked1AI, {recipient_name}!</h2>
                <p style="font-size: 16px; line-height: 1.6; color: #94a3b8;">
                    Your email has been successfully verified. Your account is now fully active, and you have access to all our AI-powered career tools.
                </p>
                <div style="text-align: center; margin: 40px 0;">
                    <a href="{APP_BASE_URL}/auth/login" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 16px; display: inline-block; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);">Login to Dashboard</a>
                </div>
                <p style="font-size: 14px; color: #64748b; margin-bottom: 0;">
                    We're excited to help you accelerate your career.
                </p>
            </div>
            <div style="background-color: #0f172a; padding: 20px; text-align: center; border-top: 1px solid #334155;">
                <p style="margin: 0; font-size: 12px; color: #475569;">&copy; 2026 Ranked1AI Team. All rights reserved.</p>
            </div>
        </div>
    </div>
    """
    result = _send_email(recipient_email, "Welcome to Ranked1AI", html_content)
    if result["success"]:
        logging.info(f"Welcome email sent to {recipient_email}")
    return result
