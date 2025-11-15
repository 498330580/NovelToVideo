# 使用Python 3.10作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p output temp data logs \
    && chmod -R 755 output temp data logs

# 暴露端口
EXPOSE 5000

# 设置卷挂载点
VOLUME ["/app/output", "/app/temp", "/app/data", "/app/logs"]

# 启动命令
CMD ["python", "run.py"]