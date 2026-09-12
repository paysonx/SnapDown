# 瞬下 SnapDown 部署镜像（预留，未经实机验证）
# 构建：docker build -t flashdown .
# 运行：docker run -p 8000:8000 -v $PWD/downloads:/app/downloads flashdown

FROM node:22-alpine AS webbuild
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY run.py ./
COPY --from=webbuild /web/dist ./frontend/dist
ENV FVD_HOST=0.0.0.0 FVD_PORT=8000
EXPOSE 8000
CMD ["python", "run.py"]
