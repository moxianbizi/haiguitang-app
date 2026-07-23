import re
import os
import hashlib
import secrets
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    soups = db.relationship("Soup", backref="author", lazy="dynamic")

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email}


class Soup(db.Model):
    __tablename__ = "soups"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    season = db.Column(db.String(64), index=True)
    episode = db.Column(db.String(16))
    title = db.Column(db.String(255), nullable=False)
    surface = db.Column(db.Text)
    base = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sort_order = db.Column(db.Integer, default=0)

    def to_dict(self, include_base=False):
        d = {
            "id": self.id,
            "filename": self.filename,
            "season": self.season or "",
            "episode": self.episode or "",
            "title": self.title,
            "surface": self.surface or "",
            "excerpt": (self.surface or "")[:80],
        }
        if include_base:
            d["base"] = self.base or ""
        return d


class Room(db.Model):
    __tablename__ = "rooms"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False, index=True)
    host_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    soup_id = db.Column(db.Integer, db.ForeignKey("soups.id"), nullable=True)
    status = db.Column(db.String(16), default="waiting")  # waiting/playing/ended
    ai_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    host = db.relationship("User", backref="rooms")
    soup = db.relationship("Soup")

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "host": self.host.to_dict() if self.host else None,
            "soup_id": self.soup_id,
            "status": self.status,
            "ai_enabled": self.ai_enabled,
        }


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    username = db.Column(db.String(64))
    msg_type = db.Column(db.String(32), nullable=False)  # chat/ai_question/ai_answer/system
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username or "",
            "msg_type": self.msg_type,
            "content": self.content,
            "created_at": self.created_at.strftime("%H:%M:%S") if self.created_at else "",
        }


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$")
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False


def parse_md(filename: str, content: str):
    """解析海龟汤 Markdown 文件。

    支持两种格式：
    1. 行内关键词：以「汤面」「汤底」开头切分（本项目实际格式）
    2. 标准标记：`## 汤面` / `## 汤底`（兼容）
    """
    lines = content.strip().split("\n")
    title = filename.replace(".md", "")
    season = ""
    episode = ""
    surface = ""
    base = ""

    # 标题：首个 `# ` 行
    for line in lines:
        if line.strip().startswith("# "):
            title = line.strip()[2:].strip()
            break

    # 优先：行内「汤面...汤底...」正则切分
    body = "\n".join(l for l in lines if not l.strip().startswith("#"))
    m = re.search(r"汤面(.+?)汤底(.+)", body, re.DOTALL)
    if m:
        surface = m.group(1).strip()
        base = m.group(2).strip()
    else:
        # 兼容 `## 汤面` / `## 汤底` 标记格式
        section = None
        for line in lines:
            s = line.strip()
            if s in ("## 汤面", "# 汤面"):
                section = "surface"
            elif s in ("## 汤底", "# 汤底"):
                section = "base"
            elif section == "surface":
                surface += line + "\n"
            elif section == "base":
                base += line + "\n"
        surface = surface.strip()
        base = base.strip()

    # season/episode 从文件名推断
    m2 = re.match(r"^(S\d+)(E\d+)", filename)
    if m2:
        season = m2.group(1)
        episode = m2.group(2)

    if not season:
        if "灵之残响" in filename:
            season = "灵之残响"
        elif "规则怪谈" in filename:
            season = "规则怪谈"

    return {
        "filename": filename,
        "season": season,
        "episode": episode,
        "title": title,
        "surface": surface,
        "base": base,
    }
