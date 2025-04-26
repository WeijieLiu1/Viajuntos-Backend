FROM python:3.8-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt /app/
RUN pip install --upgrade pip wheel setuptools && \
    pip install numpy==1.24.3 google-api-python-client==2.49.0 matplotlib==3.7.1 && \
    pip install -r requirements.txt

# 环境变量（Cloud Run 也可以在控制台设置）
ENV API_PORT=8080
ENV API_DEBUG=True
ENV PORT=8080

# 复制所有代码
COPY . .

# 启动服务（确保 wsgi.py 启动你的 Flask + SocketIO）
CMD ["python3", "wsgi.py"]
