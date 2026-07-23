import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import current_app

# 内存存储验证码 {email: (code, expire)}
_codes = {}


def send_verification_code(email: str) -> tuple:
    """发送验证码到邮箱，返回 (success, message)"""
    cfg = current_app.config
    if not cfg.get("MAIL_SMTP_HOST"):
        code = str(secrets.randbelow(900000) + 100000)
        _codes[email] = (code, datetime.now() + timedelta(minutes=10))
        return False, f"SMTP 未配置，验证码为: {code}（仅开发模式）"

    code = str(secrets.randbelow(900000) + 100000)
    _codes[email] = (code, datetime.now() + timedelta(minutes=10))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "海龟汤馆 - 验证码"
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = email

    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
      <h2 style="color: #6ee7ff;">海龟汤馆</h2>
      <p>你的注册验证码是：</p>
      <p style="font-size: 2rem; font-weight: bold; letter-spacing: 0.2em; color: #6ee7ff;">{code}</p>
      <p style="color: #888;">验证码 10 分钟内有效，请勿泄露给他人。</p>
    </div>
    """
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(cfg["MAIL_SMTP_HOST"], cfg["MAIL_SMTP_PORT"]) as server:
            server.login(cfg["MAIL_SMTP_USER"], cfg["MAIL_SMTP_PASS"])
            server.sendmail(cfg["MAIL_FROM"], [email], msg.as_string())
        return True, "验证码已发送"
    except Exception as e:
        return False, f"邮件发送失败: {e}"


def verify_code(email: str, code: str) -> bool:
    entry = _codes.get(email)
    if not entry:
        return False
    stored_code, expire = entry
    if datetime.now() > expire:
        del _codes[email]
        return False
    if stored_code == code:
        del _codes[email]
        return True
    return False
