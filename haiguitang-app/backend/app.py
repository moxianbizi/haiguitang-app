import os
import sys
from flask import Flask
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_sqlalchemy import SQLAlchemy

# 确保 backend 目录在 path 里
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models import db, User, Soup, Room, Message
from auth import auth_bp
from soups_api import soups_bp
from rooms import rooms_bp
from ai_api import ai_bp
from ai import ask_ai, AIError

socketio = SocketIO()


def create_app():
    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    app.config.from_object(Config)

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    with app.app_context():
        db.create_all()
        init_soups(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(soups_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(ai_bp, url_prefix="/api/ai")

    # --- 路由 ---

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    @app.route("/<path:path>")
    def static_proxy(path):
        full = os.path.join(app.static_folder, path)
        if os.path.isfile(full):
            return app.send_static_file(path)
        # SPA fallback
        return app.send_static_file("index.html")

    # --- WebSocket 事件 ---

    @socketio.on("join")
    def handle_join(data):
        code = (data or {}).get("code", "").upper()
        room = Room.query.filter_by(code=code).first()
        if not room:
            emit("error", {"msg": "房间不存在"})
            return
        join_room(code)
        emit("joined", {"code": code, "room": room.to_dict()})
        emit(
            "message",
            Message(
                room_id=room.id,
                msg_type="system",
                content=f"一位玩家进入了房间",
            ).to_dict(),
            to=code,
        )

    @socketio.on("leave")
    def handle_leave(data):
        code = (data or {}).get("code", "").upper()
        leave_room(code)

    @socketio.on("chat")
    def handle_chat(data):
        code = (data or {}).get("code", "").upper()
        content = (data or {}).get("content", "").strip()
        uid = (data or {}).get("user_id")

        if not content:
            return

        room = Room.query.filter_by(code=code).first()
        if not room:
            return

        username = "游客"
        if uid:
            user = db.session.get(User, uid)
            if user:
                username = user.username

        msg = Message(
            room_id=room.id,
            user_id=uid,
            username=username,
            msg_type="chat",
            content=content,
        )
        db.session.add(msg)
        db.session.commit()
        emit("message", msg.to_dict(), to=code)

    @socketio.on("ai_question")
    def handle_ai_question(data):
        code = (data or {}).get("code", "").upper()
        question = (data or {}).get("content", "").strip()
        uid = (data or {}).get("user_id")
        api_key = (data or {}).get("api_key", "")

        if not question:
            return

        room = Room.query.filter_by(code=code).first()
        if not room or not room.soup_id:
            emit("error", {"msg": "房间里还没有选汤"})
            return

        if not room.ai_enabled:
            emit("error", {"msg": "AI 未启用"})
            return

        username = "游客"
        if uid:
            user = db.session.get(User, uid)
            if user:
                username = user.username

        q_msg = Message(
            room_id=room.id,
            user_id=uid,
            username=username,
            msg_type="ai_question",
            content=question,
        )
        db.session.add(q_msg)
        db.session.commit()
        emit("message", q_msg.to_dict(), to=code)

        # 调 AI（密钥由前端用户在请求中提供，后端不存储）
        soup = room.soup
        try:
            answer = ask_ai(soup.surface, soup.base, question, api_key)
        except AIError as e:
            emit("ai_error", {"msg": e.message, "code": e.code}, to=code)
            return

        a_msg = Message(
            room_id=room.id,
            msg_type="ai_answer",
            content=answer,
        )
        db.session.add(a_msg)
        db.session.commit()
        emit("message", a_msg.to_dict(), to=code)

    return app, socketio


def init_soups(app):
    """从 soups/ 目录导入 Markdown 到数据库"""
    soups_dir = app.config["SOUPS_DIR"]
    if not os.path.isdir(soups_dir):
        return

    # 如果已有数据，跳过
    if Soup.query.count() > 0:
        return

    from models import parse_md

    files = sorted(
        f for f in os.listdir(soups_dir) if f.endswith(".md")
    )
    for idx, filename in enumerate(files):
        filepath = os.path.join(soups_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        parsed = parse_md(filename, content)
        soup = Soup(
            filename=filename,
            season=parsed["season"],
            episode=parsed["episode"],
            title=parsed["title"],
            surface=parsed["surface"],
            base=parsed["base"],
            sort_order=idx,
        )
        db.session.add(soup)

    db.session.commit()
    print(f"已导入 {len(files)} 碗海龟汤")


if __name__ == "__main__":
    app, sio = create_app()
    sio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
