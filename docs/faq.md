# 常见问题

本页面收集了使用 CDNBestIP 时的常见问题和解答。

## 安装相关

### Q: 支持哪些 Python 版本？

A: CDNBestIP 需要 Python 3.13 或更高版本。

### Q: 如何升级到最新版本？

A: 使用以下命令：

```bash
pip install --upgrade cdnbestip
```

### Q: 安装时出现权限错误怎么办？

A: 使用 `--user` 标志安装到用户目录：

```bash
pip install --user cdnbestip
```

## 使用相关

### Q: 如何只测试不更新 DNS？

A: 不使用 `-n` 参数即可：

```bash
cdnbestip -d example.com -p cf -s 2
```

### Q: 为什么没有找到满足阈值的 IP？

A: 可能的原因：

1. 速度阈值设置过高，尝试降低 `-s` 参数
2. 网络环境不佳，尝试不同的时间段
3. IP 源不适合你的地区，尝试其他 IP 源

解决方案：

```bash
# 降低阈值
cdnbestip -d example.com -p cf -s 1 -n

# 尝试不同的 IP 源
cdnbestip -i gc -d example.com -p gc -s 2 -n
```

### Q: 如何查看详细的调试信息？

A: 使用 `--debug` 参数：

```bash
cdnbestip -d example.com -p cf -s 2 -n --debug
```

### Q: 结果文件保存在哪里？

A: 
- 速度测试结果：当前目录下的 `result.csv`
- IP 列表：当前目录下的 `ip_list_*.txt`
- 日志文件：`~/.cdnbestip/logs/`
- 缓存文件：`~/.cdnbestip/cache/`
- 二进制文件：`~/.cdnbestip/bin/`

### Q: 如何清理缓存？

A: 删除缓存目录：

```bash
rm -rf ~/.cdnbestip/cache/
```

或使用 `-r` 参数强制刷新：

```bash
cdnbestip -d example.com -p cf -s 2 -n -r
```

## 认证相关

### Q: API 令牌和 API 密钥有什么区别？

A: 

| 特性 | API 令牌 | API 密钥 |
|------|----------|----------|
| 安全性 | 高（可限制权限） | 低（全局权限） |
| 推荐度 | ✅ 推荐 | ⚠️ 不推荐 |
| 使用方式 | `-t TOKEN` | `-a EMAIL -k KEY` |

### Q: 如何获取 API 令牌？

A: 

1. 登录 [CloudFlare Dashboard](https://dash.cloudflare.com/)
2. 进入 **My Profile** → **API Tokens**
3. 点击 **Create Token**
4. 选择 **Edit zone DNS** 模板
5. 配置权限并创建令牌

### Q: 认证失败怎么办？

A: 检查以下几点：

1. API 令牌/密钥是否正确
2. 令牌是否有足够的权限
3. 令牌是否已过期
4. 域名是否在你的 CloudFlare 账号下

## IP 数据源相关

### Q: 支持哪些 IP 数据源？

A: 

| 数据源 | 提供商 | 自动配置 | 推荐区域 |
|--------|--------|----------|----------|
| `cf` | CloudFlare | ✅ | 全球 |
| `gc` | GCore | ✅ | 亚太 |
| `ct` | CloudFront | ❌ | 全球 |
| `aws` | Amazon AWS | ❌ | 全球 |

### Q: 为什么 CloudFront 需要指定测试 URL？

A: CloudFront 没有统一的测试端点，需要根据你的 CloudFront 分发指定测试 URL。

```bash
cdnbestip -i ct -u https://your-distribution.cloudfront.net/test -d example.com -p ct -s 2 -n
```

### Q: 如何选择合适的 IP 数据源？

A: 根据你的目标区域选择：

- **全球用户**：使用 `cf`（CloudFlare）
- **亚太地区**：使用 `gc`（GCore）
- **AWS 基础设施**：使用 `ct`（CloudFront）或 `aws`

### Q: 可以使用自定义 IP 列表吗？

A: 可以，使用 `-i` 参数指定 URL：

```bash
cdnbestip -i https://example.com/custom-ips.txt -u https://test.example.com/file -d example.com -p custom -s 2 -n
```

## DNS 相关

### Q: 支持哪些 DNS 记录类型？

A: 支持以下类型：

- `A` - IPv4 地址（默认）
- `AAAA` - IPv6 地址
- `CNAME` - 规范名称
- `MX` - 邮件交换
- `TXT` - 文本记录
- `SRV` - 服务记录
- `NS` - 名称服务器
- `PTR` - 指针记录

### Q: 如何只更新一条 DNS 记录？

A: 使用 `-o` 参数：

```bash
cdnbestip -d example.com -p cf -s 2 -n -o
```

这将只创建/更新 `cf.example.com` 记录。

### Q: 如何限制 DNS 记录数量？

A: 使用 `-q` 参数：

```bash
# 最多创建 3 条记录
cdnbestip -d example.com -p cf -s 2 -n -q 3
```

### Q: DNS 记录会被覆盖吗？

A: 是的，如果记录已存在，会被更新为新的 IP。建议使用专门的前缀（如 `cf`、`gc`）来避免冲突。

## 性能相关

### Q: 速度测试需要多长时间？

A: 取决于多个因素：

- IP 列表大小（通常 1000-2000 个）
- 网络速度
- 速度阈值设置
- 测试超时时间

通常需要 3-10 分钟。

### Q: 如何加快测试速度？

A: 

1. 提高速度阈值（减少测试的 IP 数量）
2. 使用缓存结果（不使用 `-r`）
3. 减少超时时间（使用 `-T` 参数）

```bash
# 使用较高阈值和较短超时
cdnbestip -d example.com -p cf -s 5 -T 300 -n
```

### Q: 可以并发测试吗？

A: CloudflareSpeedTest 工具本身支持并发，CDNBestIP 会自动使用其默认并发设置。

## Docker 相关

### Q: 如何使用 Docker 运行？

A: 

```bash
docker run --rm \
  -e CLOUDFLARE_API_TOKEN="your_token" \
  idevsig/cdnbestip:latest \
  -d example.com -p cf -s 2 -n
```

### Q: 如何在 Docker 中使用定时任务？

A: 参见 [Docker 部署指南](deployment/docker.md) 中的定时任务部分。

### Q: Docker 镜像在哪里？

A: 

- Docker Hub: `idevsig/cdnbestip`
- GitHub Container Registry: `ghcr.io/idev-sig/cdnbestip`
- 腾讯云: `sgccr.ccs.tencentyun.com/idevsig/cdnbestip`
- 阿里云: `registry.cn-guangzhou.aliyuncs.com/idevsig/cdnbestip`

## 错误处理

### Q: 出现 "IP source requires custom URL" 错误

A: 某些 IP 源（如 CloudFront、AWS）需要指定测试 URL：

```bash
# ❌ 错误
cdnbestip -i ct -d example.com -p ct -s 2 -n

# ✅ 正确
cdnbestip -i ct -u https://test.cloudfront.net/file -d example.com -p ct -s 2 -n
```

### Q: 出现 "Domain not found" 错误

A: 确保域名已添加到你的 CloudFlare 账号中。

### Q: 出现 "Binary not found" 错误

A: CloudflareSpeedTest 二进制文件会自动下载。如果失败：

1. 检查网络连接
2. 检查防火墙设置
3. 手动下载并放置到 `~/.cdnbestip/bin/`

### Q: 出现 "Permission denied" 错误

A: 

1. 检查文件权限
2. 使用 `--user` 安装
3. 使用 sudo（不推荐）

## 代理相关

### Q: 如何使用代理？

A: 使用 `-x` 或 `--proxy` 参数：

```bash
cdnbestip -x http://proxy.example.com:8080 -d example.com -p cf -s 2 -n
```

### Q: 代理支持认证吗？

A: 支持，格式为：

```bash
cdnbestip -x http://username:password@proxy.example.com:8080 -d example.com -p cf -s 2 -n
```

### Q: 代理会影响测速吗？

A: 不会。代理仅用于：

- CloudFlare API 调用
- IP 列表下载

CloudflareSpeedTest 的测速过程不使用代理，确保结果准确。

## 其他问题

### Q: 如何贡献代码？

A: 参见 [贡献指南](development/contributing.md)。

### Q: 在哪里报告 Bug？

A: 在 [GitHub Issues](https://github.com/idev-sig/cdnbestip/issues) 提交问题。

### Q: 有社区讨论区吗？

A: 是的，访问 [GitHub Discussions](https://github.com/idev-sig/cdnbestip/discussions)。

### Q: 如何获取帮助？

A: 

1. 查看本文档
2. 搜索 [GitHub Issues](https://github.com/idev-sig/cdnbestip/issues)
3. 在 [Discussions](https://github.com/idev-sig/cdnbestip/discussions) 提问
4. 提交新的 Issue

## 还有问题？

如果你的问题没有在这里找到答案，请：

1. 查看 [完整文档](index.md)
2. 搜索 [GitHub Issues](https://github.com/idev-sig/cdnbestip/issues)
3. 在 [Discussions](https://github.com/idev-sig/cdnbestip/discussions) 提问
4. 提交新的 [Issue](https://github.com/idev-sig/cdnbestip/issues/new)
