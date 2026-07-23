import secrets
from flask import Blueprint, request, jsonify, session
from models import db, Room, User, Soup, Message

rooms_bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")


def _current_user():
    uid = session.get("user_id")
    if uid:
        return db.session.get(User, uid)
    return None


@rooms_bp.route("", methods=["POST"])
def create_room():
    user = _current_user()
    if not user:
        return jsonify({"error": "请先登录"}), 401

    data = request.get_json() or {}
    soup_id = data.get("soup_id")
    ai_enabled = data.get("ai_enabled", True)

    code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    # 确保唯一
    while Room.query.filter_by(code=code).first():
        code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))

    room = Room(
        code=code,
        host_id=user.id,
        soup_id=soup_id,
        ai_enabled=ai_enabled,
        status="playing",
    )
    db.session.add(room)
    db.session.commit()
    return jsonify(room.to_dict()), 201


@rooms_bp.route("/<code>", methods=["GET"])
def get_room(code):
    room = Room.query.filter_by(code=code).first()
    if not room:
        return jsonify({"error": "房间不存在"}), 404
    messages = (
        Message.query.filter_by(room_id=room.id)
        .order_by(Message.created_at)
        .all()
    )
    return jsonify(
        {
            "room": room.to_dict(),
            "messages": [m.to_dict() for m in messages],
            "soup": room.soup.to_dict(include_base=False) if room.soup else None,
        }
    )


@rooms_bp.route("", methods=["GET"])
def list_rooms():
    rooms = Room.query.filter_by(status="playing").order_by(Room.created_at.desc()).limit(50).all()
    return jsonify({"rooms": [r.to_dict() for r in rooms]})


@rooms_bp.route("/<code>", methods=["DELETE"])
def close_room(code):
    user = _current_user()
    if not user:
        return jsonify({"error": "请先登录"}), 401
    room = Room.query.filter_by(code=code).first()
    if not room:
        return jsonify({"error": "房间不存在"}), 404
    if room.host_id != user.id:
        return jsonify({"error": "只有房主可以关闭房间"}), 403
    room.status = "ended"
    db.session.commit()
    return jsonify({"msg": "已关闭"})


@rooms_bp.route("/<code>/select-soup", methods=["POST"])
def select_soup(code):
    user = _current_user()
    if not user:
        return jsonify({"error": "请先登录"}), 401
    room = Room.query.filter_by(code=code).first()
    if not room:
        return jsonify({"error": "房间不存在"}), 404
    if room.host_id != user.id:
        return jsonify({"error": "只有房主可以选汤"}), 403

    data = request.get_json() or {}
    room.soup_id = data.get("soup_id")
    db.session.commit()

    msg = Message(
        room_id=room.id,
        msg_type="system",
        content=f"房主选了一碗新汤，开始猜吧！",
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify(room.to_dict())
