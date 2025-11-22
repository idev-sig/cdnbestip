# CDNBestIP

**一个基于 CloudflareSpeedTest 获取最佳 CDN IP 的工具**

[![PyPI version](https://badge.fury.io/py/cdnbestip.svg)](https://pypi.org/project/cdnbestip/)
[![Python Version](https://img.shields.io/pypi/pyversions/cdnbestip.svg)](https://pypi.org/project/cdnbestip/)
[![License](https://img.shields.io/github/license/idev-sig/cdnbestip.svg)](https://github.com/idev-sig/cdnbestip/blob/main/LICENSE)
[![Docker Pulls](https://img.shields.io/docker/pulls/idevsig/cdnbestip.svg)](https://hub.docker.com/r/idevsig/cdnbestip)

## 功能特点

- 🚀 **自动化测速** - 基于 CloudflareSpeedTest 进行 CDN IP 速度测试
- 🌐 **DNS 管理** - 自动更新 CloudFlare DNS 记录到最佳 IP
- 📊 **多源支持** - 支持 CloudFlare、GCore、CloudFront、AWS 等 IP 数据源
- 🎯 **智能配置** - 根据 IP 源自动配置相应的测试端点
- 🔧 **灵活参数** - 完整的命令行界面与环境变量支持
- 🐳 **容器化** - Docker 支持，便于部署和定时任务
- 📝 **详细日志** - 多级别日志记录，便于调试和监控
- 🔒 **安全认证** - 支持 API 令牌和 API 密钥两种认证方式
- ⚡ **高性能** - 支持并发测试和结果缓存
- 🌍 **跨平台** - 支持 Windows、Linux、macOS 等多平台

## 快速开始

### 安装

=== "使用 pip"

    ```bash
    pip install cdnbestip
    ```

=== "使用 uv"

    ```bash
    uv tool install cdnbestip
    ```

=== "从源码安装"

    ```bash
    pip install git+https://github.com/idev-sig/cdnbestip.git
    ```

### 基本用法

```bash
# 运行速度测试
cdnbestip -d example.com -p cf -s 2

# 测试并更新 DNS 记录
cdnbestip -t YOUR_API_TOKEN -d example.com -p cf -s 2 -n
```

## 使用场景

### 场景 1: 优化网站 CDN

```bash
# 测试 CloudFlare IP 并更新 DNS
cdnbestip -i cf -d example.com -p cf -s 5 -n -q 3
```

### 场景 2: 多区域 CDN 优化

```bash
# 亚太地区使用 GCore
cdnbestip -i gc -d asia.example.com -p gc -s 3 -n

# 全球使用 CloudFlare
cdnbestip -i cf -d global.example.com -p cf -s 3 -n
```

### 场景 3: 定时自动优化

```bash
# 添加到 crontab
0 */6 * * * cdnbestip -d example.com -p cf -s 2 -n -r
```

## Docker 支持

### 快速运行

```bash
docker run --rm \
  -e CLOUDFLARE_API_TOKEN="your_token" \
  idevsig/cdnbestip:latest \
  -d example.com -p cf -s 2 -n
```

### Docker Compose

```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
      - TZ=Asia/Shanghai
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
    restart: unless-stopped
```

## 文档导航

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } __快速开始__

    ---

    快速安装和配置 CDNBestIP

    [:octicons-arrow-right-24: 开始使用](getting-started/installation.md)

-   :material-book-open-variant:{ .lg .middle } __用户指南__

    ---

    详细的使用说明和命令参考

    [:octicons-arrow-right-24: 查看指南](user-guide/cli-reference.md)

-   :material-docker:{ .lg .middle } __部署指南__

    ---

    Docker 部署方案

    [:octicons-arrow-right-24: 部署文档](deployment/docker.md)

-   :material-help-circle:{ .lg .middle } __常见问题__

    ---

    常见问题解答

    [:octicons-arrow-right-24: 查看 FAQ](faq.md)

</div>

## 支持的 IP 数据源

| 数据源 | 提供商 | 自动配置 | 推荐区域 |
|--------|--------|----------|----------|
| `cf` | CloudFlare | ✅ | 全球 |
| `gc` | GCore | ✅ | 亚太 |
| `ct` | CloudFront | ❌ | 全球 |
| `aws` | Amazon AWS | ❌ | 全球 |

## 社区与支持

- 📖 [完整文档](https://cdnbestip.ooos.top/)
- 🐛 [问题反馈](https://github.com/idev-sig/cdnbestip/issues)
- 💬 [讨论区](https://github.com/idev-sig/cdnbestip/discussions)
- 📦 [PyPI 包](https://pypi.org/project/cdnbestip/)
- 🐳 [Docker Hub](https://hub.docker.com/r/idevsig/cdnbestip)

## 许可证

本项目采用 [Apache License 2.0](https://github.com/idev-sig/cdnbestip/blob/main/LICENSE) 许可证。
