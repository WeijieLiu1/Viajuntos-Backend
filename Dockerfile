FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip wheel setuptools && \
    pip install numpy==1.24.3 google-api-python-client==2.49.0 matplotlib==3.7.1 && \
    pip install -r requirements.txt

ENV PORT=8080
ENV API_PORT=8080
ENV API_DEBUG=True

COPY . .

# 确保 entrypoint 可执行
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
