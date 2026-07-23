from flask import Blueprint, request, jsonify
from models import db, Soup
from ai import ask_ai, AIError

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/ask", methods=["POST"])
def ai_ask():
    """单人模式：玩家向 AI 主持人提问。

    请求体:
        {
            "soup_id": 1,
            "question": "主角是男性吗？",
            "api_key": "sk-..."   # 由前端用户填入，后端不存储
        }

    返回:
        { "answer": "是" }        # 成功
        { "error": "...", "code": "..." }  # 失败
    """
    data = request.get_json(silent=True) or {}

    soup_id = data.get("soup_id")
    question = (data.get("question") or "").strip()
    api_key = data.get("api_key") or ""

    if not soup_id or not question:
        return jsonify({"error": "缺少 soup_id 或 question", "code": "bad_request"}), 400

    soup = db.session.get(Soup, soup_id)
    if not soup:
        return jsonify({"error": "海龟汤不存在", "code": "not_found"}), 404

    if not soup.base:
        return jsonify({"error": "该汤没有汤底，无法提问", "code": "no_base"}), 400

    try:
        answer = ask_ai(soup.surface or "", soup.base, question, api_key)
    except AIError as e:
        return jsonify({"error": e.message, "code": e.code}), 200

    return jsonify({"answer": answer})
