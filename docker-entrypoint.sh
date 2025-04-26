#!/bin/bash

#cd /api

echo "📦 正在运行数据库迁移..."
python3 manage.py db migrate || true
python3 manage.py db upgrade || true

echo "🚀 启动 Flask 应用..."
exec python3 wsgi.py