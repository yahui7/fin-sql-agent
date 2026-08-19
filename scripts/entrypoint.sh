#!/bin/sh
# 容器启动入口：检查数据库是否已初始化，未初始化则导入数据
# 这样即使 data 目录被挂载成空目录，启动时也能自动补数据

set -e

echo "检查数据库初始化状态..."

# 检查 financial.db 是否存在
if [ -f /app/data/financial.db ]; then
    echo "✅ 数据库已存在，跳过初始化"
else
    echo "📥 数据库不存在，开始初始化（从 CSV 导入）..."
    python scripts/import_data.py
fi

echo "🚀 启动 Gunicorn..."
exec "$@"