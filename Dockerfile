# 使用Python 3.10-slim作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量（Docker生产环境配置）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production \
    PIP_NO_CACHE_DIR=1

# 安装系统依赖（gcc用于编译Python包，ffmpeg用于视频处理）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖（使用no-cache-dir减少镜像体积）
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p output temp data logs \
    && chmod -R 755 output temp data logs

# 健康检查（检查Flask应用是否正常运行）
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# 暴露端口
EXPOSE 5000

# 设置卷挂载点（支持持久化存储）
VOLUME ["/app/output", "/app/temp", "/app/data", "/app/logs"]

# 启动命令
CMD ["python", "run.py"]