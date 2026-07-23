from flask import Blueprint, request, jsonify, session
from models import db, User, hash_password, verify_password
from mail import send_verification_code, verify_code

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/send-code", methods=["POST"])
def send_code():
    data = request.get_json()
    email = (data or {}).get("email", "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "邮箱格式不正确"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "该邮箱已注册"}), 409

    ok, msg = send_verification_code(email)
    if not ok and "SMTP 未配置" not in msg:
        return jsonify({"error": msg}), 500
    return jsonify({"msg": msg})


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    code = data.get("code", "")

    if not username or len(username) < 2:
        return jsonify({"error": "用户名至少 2 个字符"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码至少 6 个字符"}), 400
    if not email:
        return jsonify({"error": "邮箱不能为空"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "用户名已存在"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "邮箱已注册"}), 409

    if not verify_code(email, code):
        return jsonify({"error": "验证码错误或已过期"}), 400

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
    )
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify({"user": user.to_dict()})


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    account = data.get("account", "").strip()
    password = data.get("password", "")

    user = User.query.filter(
        (User.username == account) | (User.email == account.lower())
    ).first()

    if not user or not verify_password(password, user.password_hash):
        return jsonify({"error": "账号或密码错误"}), 401

    session["user_id"] = user.id
    return jsonify({"user": user.to_dict()})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"msg": "已退出"})


@auth_bp.route("/me", methods=["GET"])
def me():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"user": None}), 401
    user = db.session.get(User, uid)
    if not user:
        session.pop("user_id", None)
        return jsonify({"user": None}), 401
    return jsonify({"user": user.to_dict()})
