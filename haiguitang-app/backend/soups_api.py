import os
from flask import Blueprint, request, jsonify, session, send_from_directory, current_app
from models import db, Soup, User, parse_md

soups_bp = Blueprint("soups", __name__, url_prefix="/api/soups")


def _current_user():
    uid = session.get("user_id")
    if uid:
        return db.session.get(User, uid)
    return None


@soups_bp.route("", methods=["GET"])
def list_soups():
    q = request.args.get("q", "").strip().lower()
    season = request.args.get("season", "").strip()

    query = Soup.query
    if season:
        query = query.filter_by(season=season)
    if q:
        query = query.filter(
            db.or_(
                Soup.title.ilike(f"%{q}%"),
                Soup.surface.ilike(f"%{q}%"),
                Soup.season.ilike(f"%{q}%"),
            )
        )

    soups = query.order_by(Soup.sort_order, Soup.id).all()

    seasons = [
        r[0]
        for r in db.session.query(Soup.season)
        .distinct()
        .order_by(Soup.season)
        .all()
    ]

    return jsonify(
        {
            "count": len(soups),
            "seasons": seasons,
            "soups": [s.to_dict() for s in soups],
        }
    )


@soups_bp.route("/<int:soup_id>", methods=["GET"])
def get_soup(soup_id):
    soup = db.session.get(Soup, soup_id)
    if not soup:
        return jsonify({"error": "未找到"}), 404
    return jsonify(soup.to_dict(include_base=True))


@soups_bp.route("/<int:soup_id>/download", methods=["GET"])
def download_soup(soup_id):
    soup = db.session.get(Soup, soup_id)
    if not soup:
        return jsonify({"error": "未找到"}), 404

    soups_dir = current_app.config["SOUPS_DIR"]
    filepath = os.path.join(soups_dir, soup.filename)
    if os.path.exists(filepath):
        return send_from_directory(soups_dir, soup.filename, as_attachment=True)

    # 如果文件不存在，动态生成 MD
    md_content = f"# {soup.title}\n\n"
    if soup.season:
        md_content += f"**季：**{soup.season}\n\n"
    if soup.episode:
        md_content += f"**集：**{soup.episode}\n\n"
    md_content += f"## 汤面\n\n{soup.surface}\n\n## 汤底\n\n{soup.base}\n"

    from io import BytesIO
    import flask

    buf = BytesIO(md_content.encode("utf-8"))
    return flask.send_file(
        buf,
        mimetype="text/markdown",
        as_attachment=True,
        download_name=soup.filename,
    )


@soups_bp.route("", methods=["POST"])
def create_soup():
    user = _current_user()
    if not user:
        return jsonify({"error": "请先登录"}), 401

    data = request.get_json() or {}
    title = data.get("title", "").strip()
    surface = data.get("surface", "").strip()
    base = data.get("base", "").strip()
    season = data.get("season", "").strip()
    episode = data.get("episode", "").strip()

    if not title or not surface or not base:
        return jsonify({"error": "标题、汤面、汤底不能为空"}), 400

    filename = data.get("filename", "").strip()
    if not filename:
        filename = f"{season}{episode}_{title}.md" if season else f"{title}.md"

    if Soup.query.filter_by(filename=filename).first():
        return jsonify({"error": "文件名已存在"}), 409

    max_order = db.session.query(db.func.max(Soup.sort_order)).scalar() or 0
    soup = Soup(
        filename=filename,
        season=season,
        episode=episode,
        title=title,
        surface=surface,
        base=base,
        author_id=user.id,
        sort_order=max_order + 1,
    )
    db.session.add(soup)
    db.session.commit()

    # 写 MD 文件
    soups_dir = current_app.config["SOUPS_DIR"]
    os.makedirs(soups_dir, exist_ok=True)
    md_content = f"# {title}\n\n"
    if season:
        md_content += f"**季：**{season}\n\n"
    if episode:
        md_content += f"**集：**{episode}\n\n"
    md_content += f"## 汤面\n\n{surface}\n\n## 汤底\n\n{base}\n"
    with open(os.path.join(soups_dir, filename), "w", encoding="utf-8") as f:
        f.write(md_content)

    return jsonify(soup.to_dict(include_base=True)), 201


@soups_bp.route("/<int:soup_id>", methods=["PUT"])
def update_soup(soup_id):
    user = _current_user()
    if not user:
        return jsonify({"error": "请先登录"}), 401

    soup = db.session.get(Soup, soup_id)
    if not soup:
        return jsonify({"error": "未找到"}), 404

    data = request.get_json() or {}
    for field in ("title", "surface", "base", "season", "episode"):
        if field in data:
            setattr(soup, field, data[field].strip() if isinstance(data[field], str) else data[field])

    db.session.commit()

    # 同步写 MD 文件
    soups_dir = current_app.config["SOUPS_DIR"]
    md_content = f"# {soup.title}\n\n"
    if soup.season:
        md_content += f"**季：**{soup.season}\n\n"
    if soup.episode:
        md_content += f"**集：**{soup.episode}\n\n"
    md_content += f"## 汤面\n\n{soup.surface}\n\n## 汤底\n\n{soup.base}\n"
    with open(os.path.join(soups_dir, soup.filename), "w", encoding="utf-8") as f:
        f.write(md_content)

    return jsonify(soup.to_dict(include_base=True))


@soups_bp.route("/<int:soup_id>", methods=["DELETE"])
def delete_soup(soup_id):
    user = _current_user()
    if not user:
        return jsonify({"error": "请先登录"}), 401

    soup = db.session.get(Soup, soup_id)
    if not soup:
        return jsonify({"error": "未找到"}), 404

    # 删 MD 文件
    soups_dir = current_app.config["SOUPS_DIR"]
    filepath = os.path.join(soups_dir, soup.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(soup)
    db.session.commit()
    return jsonify({"msg": "已删除"})
