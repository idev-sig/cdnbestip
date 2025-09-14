# CDNBestIP

一个基于 [**CloudflareSpeedTest**](https://github.com/XIU2/CloudflareSpeedTest) 获取最佳 CDN IP 的工具，用于自动测速并更新最佳的 CDN IP 到 Cloudflare DNS 记录。

## 功能特点

- 🚀 **自动化测速**：基于 CloudflareSpeedTest 进行 CDN IP 速度测试
- 🌐 **DNS 管理**：自动更新 CloudFlare DNS 记录到最佳 IP
- 📊 **多源支持**：支持 CloudFlare、GCore、CloudFront、AWS 等 IP 数据源
- 🎯 **智能配置**：根据 IP 源自动配置相应的测试端点
- 🔧 **灵活参数**：完整的命令行界面与环境变量支持
- 🐳 **容器化**：Docker 支持，便于部署和定时任务
- 📝 **详细日志**：多级别日志记录，便于调试和监控
- 🔒 **安全认证**：支持 API 令牌和 API 密钥两种认证方式
- ⚡ **高性能**：支持并发测试和结果缓存
- 🌍 **跨平台**：支持 Windows、Linux、macOS 等多平台

## 快速开始

### 安装

```bash
# 使用 pip 安装
pip install cdnbestip

# 使用 pip + git 安装
pip install git+https://github.com/idev-sig/cdnbestip.git

# 或使用 uv 安装
uv tool install git+https://github.com/idev-sig/cdnbestip.git

# 指定版本
uv tool install git+https://github.com/idev-sig/cdnbestip.git@v0.1.0
```

### 基本用法

```bash
# 运行速度测试
cdnbestip -d example.com -p cf -s 2

# 测试并更新 DNS 记录
cdnbestip -t YOUR_API_TOKEN -d example.com -p cf -s 2 -n
```

详细使用说明请参阅 [使用指南](USAGE.md)。

## Docker 支持

### 镜像获取

#### 本地构建

```bash
docker buildx bake
```

#### 使用预构建镜像

> **版本标签：** `latest`, `main`, `<TAG>`

| Registry                                                                                | Image                                              |
| --------------------------------------------------------------------------------------- | -------------------------------------------------- |
| [**Docker Hub**](https://hub.docker.com/r/idevsig/cdnbestip/)                               | `idevsig/cdnbestip`                                    |
| [**GitHub Container Registry**](https://github.com/idev-sig/cdnbestip/pkgs/container/cdnbestip) | `ghcr.io/idev-sig/cdnbestip`                           |
| **Tencent Cloud Container Registry（SG）**                                                | `sgccr.ccs.tencentyun.com/idevsig/cdnbestip`           |
| **Aliyun Container Registry（GZ）**                                                       | `registry.cn-guangzhou.aliyuncs.com/idevsig/cdnbestip` |

```bash
# 拉取镜像
docker pull idevsig/cdnbestip:latest

# 或者
docker pull ghcr.io/idev-sig/cdnbestip:latest
```

## 使用

### Python 使用方式

**先决条件：**
- Python 3.13 以上
- [CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest) v2.3.4 以上

1. 安装 
```bash
# 使用 pip 安装
pip install git+https://github.com/idev-sig/cdnbestip.git

# 或使用 uv 安装
uv tool install git+https://github.com/idev-sig/cdnbestip.git

# 指定版本或分支
uv tool install git+https://github.com/idev-sig/cdnbestip.git@v0.1.0
```

2. 使用
```bash
# 基本用法（使用邮箱）
cdnbestip -a user@example.com -k api_key -d example.com -p cf -s 5 -n -o

# 使用 GCore IP 源（自动使用 GCore 测试端点）
cdnbestip -a user@example.com -k api_key -d example.com -p gc -s 5 -n -o -i gc

# 使用 GCore IP 源 + 自定义测试 URL
cdnbestip -a user@example.com -k api_key -d example.com -p gc -s 5 -n -o -i gc -u https://hk2-speedtest.tools.gcore.com/speedtest-backend/garbage.php?ckSize=1000
```

### Docker 使用方式

#### 单次运行

```bash
# 基本用法（使用邮箱）
docker run --rm idevsig/cdnbestip:latest cdnbestip -a user@example.com -k api_key -d example.com -p cf -s 5 -n -o

# 使用 GCore IP 源（自动使用 GCore 测试端点）
docker run --rm idevsig/cdnbestip:latest cdnbestip -a user@example.com -k api_key -d example.com -p gc -s 5 -n -o -i gc

# 使用 GCore IP 源 + 自定义测试 URL
docker run --rm idevsig/cdnbestip:latest cdnbestip -a user@example.com -k api_key -d example.com -p gc -s 5 -n -o -i gc -u https://hk2-speedtest.tools.gcore.com/speedtest-backend/garbage.php?ckSize=1000
```

#### 使用 Docker Compose

1. 创建 `docker-compose.yml` 文件：

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    container_name: cdnbestip
    restart: unless-stopped
    environment:
      - CLOUDFLARE_EMAIL=user@example.com
      - CLOUDFLARE_API_KEY=api_key
      - TZ=Asia/Shanghai
    command: ["daemon"]
```

2. 启动服务：

```bash
docker compose up -d
```

3. 配置定时任务：

```bash
# 添加定时计划 (每天凌晨4:15运行)
docker exec cdnbestip sh -c "echo '15 4 * * * cd /app; cdnbestip -d example.com -p cf -r -n -q 5' | crontab -"

# 启用定时服务
docker exec -d cdnbestip crond -b -l 8

# 管理定时服务
# 停止
docker exec cdnbestip pkill crond
# 重启
docker exec cdnbestip pkill -HUP crond
```

## 文档

- [使用指南](USAGE.md) - 完整的命令行参数和使用示例
- [部署指南](DEPLOYMENT.md) - 部署和分发信息

## 帮助

```
usage: cdnbestip [-h] [-a EMAIL] [-k API_KEY] [-t API_TOKEN] [-d DOMAIN] [-p PREFIX] [--type TYPE] [-s THRESHOLD] [-P PORT] [-u URL]
                 [-T SECONDS] [-q COUNT] [-i SOURCE] [-r] [-n] [-o] [-c URL] [-e STRING] [--debug] [-v]
                 [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--no-console-log] [--no-file-log] [--version]

CloudFlare DNS speed testing and management tool

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit

CloudFlare Credentials:
  -a, --account EMAIL              CloudFlare account email
  -k, --key API_KEY                CloudFlare API key
  -t, --token API_TOKEN            CloudFlare API token (alternative to key+email)

DNS Settings:
  -d, --domain DOMAIN   Domain name (required for DNS operations)
  -p, --prefix PREFIX   DNS record prefix (required for DNS operations)
  -y, --type TYPE       DNS record type (default: A)

Speed Test Settings:
  -s, --speed THRESHOLD
                        Download speed threshold in MB/s (default: 2.0)
  -P, --port PORT       Speed test port (0-65535)
  -u, --url URL         Speed test URL
  -T, --timeout SECONDS
                        Speed test timeout in seconds (default: 600)
  -q, --quantity COUNT  Number of DNS records to create (default: 0 = unlimited)

IP Data Source:
  -i, --ipurl SOURCE    IP data source: cf, gc, ct, aws, or custom URL

Operations:
  -r, --refresh         Force refresh result.csv file
  -n, --dns             Update DNS records after speed test
  -o, --only            Only update one DNS record (fastest IP)

Advanced Options:
  -c, --cdn URL         CDN URL for file acceleration
  -e, --extend STRING   Extended parameters for CloudflareSpeedTest (use -e="-param" or -e "\\-param")
  -x, --proxy URL       Proxy URL for Cloudflare API and IP list downloads

Logging and Debugging:
  -g, --debug           Enable debug mode with detailed logging
  -v, --verbose         Enable verbose output
  -l, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set logging level (default: INFO)
  -C, --no-console-log  Disable console logging
  -F, --no-file-log     Disable file logging

Examples:
  cdnbestip -a user@example.com -k api_key -d example.com -p cf -s 2 -n -o
  
  export CLOUDFLARE_API_KEY="api_key"
  export CLOUDFLARE_EMAIL="user@example.com"
  cdnbestip -d example.com -p cf -s 2 -n -o

IP Data Sources:
  cf   - CloudFlare IPs
  gc   - GCore IPs  
  ct   - CloudFront IPs
  aws  - Amazon AWS IPs
  <url> - Custom IP data URL

Zone Types:
  A, AAAA, CNAME, MX, TXT, SRV, NS, PTR
```

### 参数说明

**CloudFlare 认证：**
> `-a` / `--account`:          CloudFlare 账号邮箱
> `-k` / `--key`:              CloudFlare API 密钥   
> `-t` / `--token`:            CloudFlare API 令牌（推荐，可替代 key+email）   

**DNS 设置：**
> `-d` / `--domain`:           域名（DNS 操作必需）   
> `-p` / `--prefix`:           DNS 记录前缀（DNS 操作必需）   
> `-y` / `--type`:             DNS 记录类型（默认：A）   

**速度测试设置：**
> `-s` / `--speed`:            下载速度阈值，单位 MB/s（默认：2.0）     
> `-P` / `--port`:             速度测试端口（0-65535）   
> `-u` / `--url`:              速度测试 URL   
> `-T` / `--timeout`:          速度测试超时时间，单位秒（默认：600）   
> `-q` / `--quantity`:         创建的 DNS 记录数量（默认：0 = 无限制）   

**IP 数据源：**
> `-i` / `--ipurl`:            IP 数据源：cf, gc, ct, aws 或自定义 URL   

**操作选项：**
> `-r` / `--refresh`:          强制刷新 result.csv 文件    
> `-n` / `--dns`:              测试后更新 DNS 记录   
> `-o` / `--only`:             仅更新一条 DNS 记录（最快的 IP）   

**高级选项：**
> `-c` / `--cdn`:              文件加速的 CDN URL     
> `-e` / `--extend`:           CloudflareSpeedTest 的扩展参数 (使用 -e="-参数" 或 -e "\\-参数")   
> `-x` / `--proxy`:            代理服务器 URL，用于 Cloudflare API 和 IP 列表下载   

**日志和调试：**
> `-g` / `--debug`:            启用调试模式和详细日志   
> `-v` / `--verbose`:          启用详细输出   
> `-l` / `--log-level`:        设置日志级别   
> `-C` / `--no-console-log`:   禁用控制台日志   
> `-F` / `--no-file-log`:      禁用文件日志   

### 认证方式

- **方式一（推荐）**：使用 API 令牌 `-t` 或设置环境变量 `CLOUDFLARE_API_TOKEN`
- **方式二**：使用 API 密钥 + 邮箱 `-k` + `-a` 或设置环境变量 `CLOUDFLARE_API_KEY` + `CLOUDFLARE_EMAIL`

**账号参数支持格式：**
- 邮箱格式：`user@example.com`
- 账号ID格式：`b9b779dc8c2e097c2a467261a8fa0000`（32位十六进制字符串）

获取 API 令牌：[CloudFlare Dashboard](https://dash.cloudflare.com/profile/api-tokens) -> `API Tokens` -> `Create Token`   
获取 API 密钥：[CloudFlare Dashboard](https://dash.cloudflare.com/profile/api-tokens) -> `API Keys` -> `Global API Key`   

### 代理配置

工具支持通过代理服务器进行 Cloudflare API 调用和 IP 列表下载。支持的代理类型：

- **HTTP 代理**：`http://proxy.example.com:8080`
- **HTTPS 代理**：`https://proxy.example.com:8080`

**使用方式：**

```bash
# 命令行参数（长参数）
cdnbestip --proxy http://proxy.example.com:8080 -d example.com -p cf -s 2 -n

# 命令行参数（短参数）
cdnbestip -x http://proxy.example.com:8080 -d example.com -p cf -s 2 -n

# 环境变量
export CDNBESTIP_PROXY="http://proxy.example.com:8080"
cdnbestip -d example.com -p cf -s 2 -n
```

**注意：** 代理仅用于 Cloudflare API 调用和 IP 列表下载，不影响 CloudflareSpeedTest 工具的测速过程。

## IP 数据源和测试端点

### 自动配置（推荐）

工具会根据选择的 IP 数据源自动配置相应的测试端点：

| IP 源 | 提供商 | 自动测试端点 | 需要 `-u` 参数？ |
|-------|--------|-------------|-----------------|
| `cf` | CloudFlare | `https://cf.xiu2.xyz/url` | 否 |
| `gc` | GCore | `https://hk2-speedtest.tools.gcore.com/speedtest-backend/garbage.php?ckSize=1000` | 否 |
| `ct` | CloudFront | 无 | **是** |
| `aws` | Amazon AWS | 无 | **是** |
| 自定义 URL | 自定义 | 无 | **是** |

### 使用示例

```bash
# 无 IP 源 - 使用 CloudflareSpeedTest 默认设置
cdnbestip -d example.com -p cf -s 2 -n

# CloudFlare IP 源 - 自动使用 CF 测试端点
cdnbestip -i cf -d example.com -p cf -s 2 -n

# GCore IP 源 - 自动使用 GCore 测试端点
cdnbestip -i gc -d example.com -p gc -s 2 -n

# CloudFront IP 源 - 需要指定测试 URL
cdnbestip -i ct -u https://example.cloudfront.net/test -d example.com -p ct -s 2 -n

# 自定义测试 URL（覆盖默认设置）
cdnbestip -i gc -u https://custom-test.example.com/test -d example.com -p gc -s 2 -n

# 使用扩展参数传递给 CloudflareSpeedTest
cdnbestip -d example.com -p cf -e="-cfcolo HKG" -s 2 -n
cdnbestip -d example.com -p cf -e "\-cfcolo HKG -a 1" -s 2 -n

# 使用代理服务器
cdnbestip -d example.com -p cf --proxy http://proxy.example.com:8080 -s 2 -n
```

### 手动指定测试 URL（`-u` 或 `--url` 参数）

#### [CloudFlare](https://www.cloudflare.com/)

```bash
# CloudFlare 官方测试端点
https://speed.cloudflare.com/__down?during=download&bytes=104857600

# 第三方 CloudFlare 测试端点
https://cf.xiu2.xyz/url
```

> `bytes` 为文件大小。`104857600` 为 `100MB`。

#### [GCore](https://gcore.com/)

**香港：**
```bash
https://hk2-speedtest.tools.gcore.com/speedtest-backend/garbage.php?ckSize=100
```

**日本：**
```bash
https://cc1-speedtest.tools.gcore.com/speedtest-backend/garbage.php?ckSize=100
```

**新加坡：**
```bash
https://sg1-speedtest.tools.gcore.com/speedtest-backend/garbage.php?ckSize=100
```

> `ckSize` 为文件大小，单位 `MB`。可自行修改，最大为 100MB。

#### [CacheFly](https://www.cachefly.com/)

```bash
https://cachefly.cachefly.net/100mb.test
```

#### [AWS CloudFront](https://aws.amazon.com/cloudfront/)

```bash
# AWS 静态资源端点示例
https://d1.awsstatic.com/logos/aws-logo-lockups/poweredbyaws/PB_AWS_logo_RGB_REV_SQ.8c88ac215fe4e441dc42865dd6962ed4f444a90d.png
```

## 许可证

本项目采用 Apache License 2.0 许可证。

## 仓库镜像

* [https://git.jetsung.com/idev/cdnbestip](https://git.jetsung.com/idev/cdnbestip)
* [https://framagit.org/idev/cdnbestip](https://framagit.org/idev/cdnbestip)
* [https://gitcode.com/idev/cdnbestip](https://gitcode.com/idev/cdnbestip)
* [https://github.com/idev-sig/cdnbestip](https://github.com/idev-sig/cdnbestip)
