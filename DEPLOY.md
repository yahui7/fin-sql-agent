# 部署指南（阿里云 ECS + Docker）

> 目标：将 Fin SQL Agent 部署到阿里云 ECS，通过域名 `yahui.org.cn` 对外提供服务。

## 架构

```
浏览器 → https://yahui.org.cn
  → ECS 公网 IP (80/443)
  → nginx 容器（反代）
  → agent 容器 (127.0.0.1:8765 内部)
  → SQLite (data/financial.db)
```

## 前置条件

1. 阿里云 ECS（2核2G，Ubuntu 22.04），已备案域名 `yahui.org.cn`
2. 域名 A 记录解析到 ECS 公网 IP

## 一、安装 Docker

```bash
# SSH 登录 ECS 后执行
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 退出重新登录，使权限生效

# 安装 docker compose
sudo apt install -y docker-compose-plugin

# 验证
docker --version
docker compose version
```

## 二、上传代码

```bash
# 方式 A：git clone（推荐）
git clone <你的仓库地址>
cd fin-sql-agent

# 方式 B：scp 上传
# scp -r 本地项目目录 root@你的IP:/home/
```

## 三、配置环境变量

```bash
# 创建生产环境变量文件（docker compose 会自动读取 .env）
cat > .env << 'EOF'
DEEPSEEK_API_KEY=你的API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
EOF
```

> ⚠️ `.env` 已在 `.gitignore` 和 `.dockerignore` 中，不会进入镜像或仓库。

## 四、构建并启动

```bash
# 构建镜像 + 后台启动
docker compose up -d --build

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f agent
```

## 五、验证

```bash
# 本机访问（nginx 映射到 80）
curl http://localhost

# 应该返回登录页 HTML
```

## 六、配置 HTTPS（可选但推荐）

```bash
# 在宿主机安装 certbot
sudo apt install -y certbot

# 暂停容器（释放 80 端口给 certbot 验证）
docker compose down

# 申请证书
sudo certbot certonly --standalone -d yahui.org.cn

# 证书会生成在 /etc/letsencrypt/live/yahui.org.cn/

# 修改 nginx/nginx.conf 加 SSL，然后：
docker compose up -d
```

## 常用运维命令

```bash
docker compose logs -f agent        # 看 agent 日志
docker compose restart agent        # 重启 agent
docker compose down                 # 停止所有
docker compose up -d --build        # 重新构建并启动
docker exec -it fin-sql-agent sh    # 进入容器调试
```

## 更新代码流程

```bash
git pull                           # 拉取最新代码
docker compose up -d --build        # 重新构建 + 启动
```