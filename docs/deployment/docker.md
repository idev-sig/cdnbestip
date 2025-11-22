# Docker 部署

本指南介绍如何使用 Docker 部署 CDNBestIP。

## 镜像获取

### 预构建镜像

CDNBestIP 提供多个镜像仓库：

| 镜像仓库 | 镜像地址 | 推荐区域 |
|----------|----------|----------|
| Docker Hub | `idevsig/cdnbestip` | 全球 |
| GitHub Container Registry | `ghcr.io/idev-sig/cdnbestip` | 全球 |
| 腾讯云容器镜像服务 | `sgccr.ccs.tencentyun.com/idevsig/cdnbestip` | 中国 |
| 阿里云容器镜像服务 | `registry.cn-guangzhou.aliyuncs.com/idevsig/cdnbestip` | 中国 |

### 拉取镜像

=== "Docker Hub"

    ```bash
    docker pull idevsig/cdnbestip:latest
    ```

=== "GitHub Container Registry"

    ```bash
    docker pull ghcr.io/idev-sig/cdnbestip:latest
    ```

=== "腾讯云"

    ```bash
    docker pull sgccr.ccs.tencentyun.com/idevsig/cdnbestip:latest
    ```

=== "阿里云"

    ```bash
    docker pull registry.cn-guangzhou.aliyuncs.com/idevsig/cdnbestip:latest
    ```

### 版本标签

- `latest` - 最新稳定版本
- `main` - 主分支最新构建
- `v0.1.0` - 特定版本

## 基本使用

### 单次运行

```bash
docker run --rm \
  -e CLOUDFLARE_API_TOKEN="your_token" \
  idevsig/cdnbestip:latest \
  -d example.com -p cf -s 2 -n
```

### 使用 API 密钥

```bash
docker run --rm \
  -e CLOUDFLARE_EMAIL="your@email.com" \
  -e CLOUDFLARE_API_KEY="your_key" \
  idevsig/cdnbestip:latest \
  -d example.com -p cf -s 2 -n
```

### 挂载配置文件

```bash
docker run --rm \
  -v $(pwd)/.env:/app/.env:ro \
  idevsig/cdnbestip:latest \
  -d example.com -p cf -s 2 -n
```

## Docker Compose

### 基本配置

创建 `docker-compose.yml`：

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    container_name: cdnbestip
    restart: unless-stopped
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
      - TZ=Asia/Shanghai
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
```

创建 `.env` 文件：

```bash
CLOUDFLARE_API_TOKEN=your_token_here
```

启动服务：

```bash
docker compose up -d
```

### 多域名配置

```yaml
services:
  cdnbestip-domain1:
    image: idevsig/cdnbestip:latest
    container_name: cdnbestip-domain1
    restart: unless-stopped
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
      - TZ=Asia/Shanghai
    command: ["-d", "domain1.com", "-p", "cf", "-s", "2", "-n", "-q", "3"]

  cdnbestip-domain2:
    image: idevsig/cdnbestip:latest
    container_name: cdnbestip-domain2
    restart: unless-stopped
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
      - TZ=Asia/Shanghai
    command: ["-d", "domain2.com", "-p", "gc", "-s", "2", "-n", "-i", "gc"]
```

### 使用代理

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
      - CDNBESTIP_PROXY=http://proxy.example.com:8080
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
```

## 定时任务

### 使用 Cron

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    container_name: cdnbestip
    restart: unless-stopped
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
      - TZ=Asia/Shanghai
    command: ["daemon"]  # 保持容器运行
```

进入容器配置 cron：

```bash
# 添加定时任务（每天凌晨 4:15 运行）
docker exec cdnbestip sh -c "echo '15 4 * * * cd /app; cdnbestip -d example.com -p cf -r -n -q 5' | crontab -"

# 启动 cron 服务
docker exec -d cdnbestip crond -b -l 8

# 查看 cron 任务
docker exec cdnbestip crontab -l

# 停止 cron 服务
docker exec cdnbestip pkill crond

# 重启 cron 服务
docker exec cdnbestip pkill -HUP crond
```

### 查看日志

```bash
# 查看容器日志
docker logs cdnbestip

# 实时查看日志
docker logs -f cdnbestip

# 查看最近 100 行日志
docker logs --tail 100 cdnbestip
```

## 数据持久化

### 挂载数据目录

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    volumes:
      - ./data:/root/.cdnbestip
      - ./results:/app
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
```

这将保存：
- 缓存文件到 `./data/cache/`
- 日志文件到 `./data/logs/`
- 二进制文件到 `./data/bin/`
- 结果文件到 `./results/`

## 网络配置

### 使用自定义网络

```yaml
networks:
  cdnbestip-network:
    driver: bridge

services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    networks:
      - cdnbestip-network
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
```

### 使用主机网络

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    network_mode: host
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
```

## 资源限制

### 限制 CPU 和内存

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
```

## 健康检查

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    healthcheck:
      test: ["CMD", "cdnbestip", "--version"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
```

## 故障排除

### 查看容器状态

```bash
docker ps -a
docker inspect cdnbestip
```

### 进入容器调试

```bash
docker exec -it cdnbestip sh
```

### 查看环境变量

```bash
docker exec cdnbestip env
```

### 重启容器

```bash
docker restart cdnbestip
```

### 清理容器

```bash
# 停止并删除容器
docker compose down

# 删除所有相关资源
docker compose down -v
```

## 安全建议

### 使用 Secrets

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    secrets:
      - cloudflare_token
    environment:
      - CLOUDFLARE_API_TOKEN_FILE=/run/secrets/cloudflare_token
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]

secrets:
  cloudflare_token:
    file: ./secrets/cloudflare_token.txt
```

### 使用非 root 用户

```dockerfile
FROM idevsig/cdnbestip:latest
USER 1000:1000
```

### 只读文件系统

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    read_only: true
    tmpfs:
      - /tmp
      - /root/.cdnbestip
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
```

## 下一步

- 查看 [命令行参数参考](../user-guide/cli-reference.md) 了解更多选项
- 阅读 [常见问题](../faq.md) 解决疑问
