import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'haiguitang.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 汤源目录
    SOUPS_DIR = os.environ.get("SOUPS_DIR", os.path.join(BASE_DIR, "soups"))

    # DeepSeek API —— 仅保留公开的接入地址与模型名，密钥由前端用户自行填写
    DEEPSEEK_BASE_URL = os.environ.get(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
    )
    DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    # SMTP
    MAIL_SMTP_HOST = os.environ.get("MAIL_SMTP_HOST", "")
    MAIL_SMTP_PORT = int(os.environ.get("MAIL_SMTP_PORT", "465"))
    MAIL_SMTP_USER = os.environ.get("MAIL_SMTP_USER", "")
    MAIL_SMTP_PASS = os.environ.get("MAIL_SMTP_PASS", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "")

    # 管理员
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
