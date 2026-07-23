# 海龟汤馆全栈版 - Zeabur/Render 通用镜像
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制前后端代码和汤源
COPY backend ./backend
COPY frontend ./frontend
COPY soups ./soups

# Zeabur/Render 都会注入 PORT 环境变量
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

WORKDIR /app/backend
CMD ["sh", "-c", "gunicorn -w 1 -b 0.0.0.0:${PORT:-8080} app:app"]
