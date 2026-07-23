import requests
from flask import current_app

SYSTEM_PROMPT = """你是海龟汤的主持人。规则如下：

1. 玩家会向你提问，你必须只回答「是」「否」或「无关」。
2. 「是」表示玩家的提问与汤底有关且正确。
3. 「否」表示玩家的提问与汤底有关但方向错误。
4. 「无关」表示玩家的提问与汤底无关。
5. 不得透露汤底内容。
6. 如果玩家直接猜中汤底的核心真相，回答「恭喜你猜中了！」

你只能从以下三个词中选一个回答：是、否、无关。
除非玩家猜中汤底，才能说「恭喜你猜中了！」。"""


class AIError(Exception):
    """AI 调用失败"""

    def __init__(self, message: str, code: str = "ai_error"):
        super().__init__(message)
        self.message = message
        self.code = code


def ask_ai(surface: str, base: str, question: str, api_key: str) -> str:
    """向 DeepSeek 发送玩家提问，返回 AI 回答。

    api_key 由调用方（前端用户）提供，后端不存储任何密钥。
    """
    cfg = current_app.config

    api_key = (api_key or "").strip()
    if not api_key:
        raise AIError("未提供 DeepSeek API Key，请在页面设置中填写。", "missing_key")

    user_content = f"""汤面（玩家已知）：{surface}
汤底（仅你可知，不可透露）：{base}

玩家提问：{question}"""

    try:
        resp = requests.post(
            f"{cfg['DEEPSEEK_BASE_URL']}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": cfg["DEEPSEEK_MODEL"],
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 64,
                "temperature": 0.3,
            },
            timeout=30,
        )
    except requests.exceptions.Timeout:
        raise AIError("AI 思考超时，请重试。", "timeout")
    except Exception as e:
        raise AIError(f"AI 调用失败：{e}", "request_error")

    if resp.status_code == 401:
        raise AIError("DeepSeek API Key 无效或已过期，请检查后重新填写。", "invalid_key")
    if resp.status_code == 402:
        raise AIError("DeepSeek 账户余额不足。", "insufficient_balance")
    if not resp.ok:
        # 透传上游错误信息（截断避免泄露过多）
        try:
            detail = resp.json().get("error", {}).get("message", resp.text[:120])
        except Exception:
            detail = resp.text[:120]
        raise AIError(f"AI 服务返回错误 ({resp.status_code})：{detail}", "upstream_error")

    try:
        data = resp.json()
        answer = data["choices"][0]["message"]["content"].strip()
        return answer
    except Exception:
        raise AIError("AI 返回内容解析失败。", "parse_error")
