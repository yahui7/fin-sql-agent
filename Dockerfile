# Fin SQL Agent — Docker 镜像
# 国内部署：基础镜像用华为云源（docker.io 被墙）
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置时区（避免时间相关查询偏差）
ENV TZ=Asia/Shanghai

# 先复制依赖文件，利用 Docker 层缓存（依赖不变就不用重装）
COPY requirements.txt .

# 安装依赖（用阿里云 pip 源，files.pythonhosted.org 被墙）
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com

# 复制项目代码
COPY . .

# 生成 SQLite 数据库（从 CSV 导入）
RUN python scripts/import_data.py

# 暴露端口（容器内 Gunicorn 监听 8765，由 nginx 反代）
EXPOSE 8765

# 启动命令：Gunicorn + Uvicorn worker
# 内网部署用 --bind 0.0.0.0，因为 nginx 在另一个容器里，通过 docker 网络访问
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", \
     "web.app:app", "--bind", "0.0.0.0:8765", "--timeout", "300"]