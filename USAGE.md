# 使用指南

本指南提供了使用CDNBESTIP Python包的全面文档。

## 命令行界面

### 基本语法

```bash
cdnbestip [OPTIONS]
```

### 认证选项

#### CloudFlare 凭证

**选项 1: API 令牌（推荐）**
```bash
cdnbestip -t YOUR_API_TOKEN [其他选项]
# 或设置环境变量
export CLOUDFLARE_API_TOKEN="YOUR_API_TOKEN"
```

**选项 2: API 密钥 + 电子邮件**
```bash
# 使用邮箱
cdnbestip -a your_email@example.com -k YOUR_API_KEY [其他选项]
# 或设置环境变量
export CLOUDFLARE_EMAIL="your_email@example.com"
export CLOUDFLARE_API_KEY="YOUR_API_KEY"
```

### DNS 设置

| 选项 | 描述 | 示例 |
|--------|-------------|---------|
| `-d, --domain` | 目标域名 | `-d example.com` |
| `-p, --prefix` | DNS记录前缀 | `-p cf` |
| `-y, --type` | DNS记录类型 | `-y A`（默认） |

### 速度测试设置

| 选项 | 描述 | 默认值 | 示例 |
|--------|-------------|---------|---------|
| `-s, --speed` | 速度阈值 (MB/s) | 0.0 | `-s 5.0` |

**注意：** 当 `-s` 为 0 时，不进行速度过滤，仅使用延迟过滤。当 `-s` 大于 0 时，同时使用速度和延迟过滤。
| `-P, --port` | 测试端口 | 443 | `-P 80` |
| `-u, --url` | 测试URL | 自动 | `-u https://speed.cloudflare.com/__down?bytes=25000000` |
| `-q, --quantity` | 最大DNS记录数 | 0 (无限制) | `-q 5` |

### IP数据源

| 选项 | 来源 | 描述 | 默认测试端点 | 需要 `-u`？ |
|--------|--------|-------------|-------------|------------|
| 无 | CloudflareSpeedTest | 使用工具默认设置 | 工具默认 | 否 |
| `-i cf` | CloudFlare | CloudFlare IPv4地址段 | `https://cf.xiu2.xyz/url` | 否 |
| `-i gc` | GCore | GCore CDN IP地址 | `https://hk2-speedtest.tools.gcore.com/speedtest-backend/garbage.php?ckSize=100` | 否 |
| `-i ct` | CloudFront | AWS CloudFront IP地址段 | 无 | **是** |
| `-i aws` | AWS | Amazon Web Services IP地址段 | 无 | **是** |
| `-i URL` | 自定义 | 自定义IP列表URL | 无 | **是** |

### 操作标志

| 标志 | 描述 |
|------|-------------|
| `-r, --refresh` | 强制刷新result.csv |
| `-n, --dns` | 更新DNS记录 |
| `-o, --only` | 仅更新一条记录（最快的IP）|

### 高级选项

| 选项 | 描述 | 示例 |
|--------|-------------|----------|
| `-c, --cdn` | 用于加速的 CDN URL | `-c https://fastfile.asfd.cn/` |
| `-e, --extend` | CloudflareSpeedTest的扩展参数 | `-e="-cfcolo HKG"` 或 `-e "\-cfcolo HKG"` |
| `-x, --proxy` | 代理服务器 URL | `-x http://proxy.example.com:8080` |

### 调试和日志选项

| 选项 | 描述 | 示例 |
|--------|-------------|----------|
| `-D, --debug` | 启用调试模式 | `-D` |
| `-v, --verbose` | 启用详细输出 | `-v` |
| `-L, --log-level` | 设置日志级别 | `-L DEBUG` |
| `-C, --no-console-log` | 禁用控制台日志 | `-C` |
| `-F, --no-file-log` | 禁用文件日志 | `-F` |
| `-V, --version` | 显示版本信息 | `-V` |

## IP 数据源和测试端点配置

### 自动配置逻辑

工具根据选择的 IP 数据源自动配置相应的测试端点：

1. **无 `-i` 参数**：不传递测试 URL 给 CloudflareSpeedTest，使用工具默认设置
2. **`-i cf`**：自动使用 CloudFlare 默认测试端点，除非用 `-u` 覆盖
3. **`-i gc`**：自动使用 GCore 默认测试端点，除非用 `-u` 覆盖
4. **`-i ct/aws`**：必须使用 `-u` 指定测试端点，否则报错
5. **自定义 IP 源**：必须使用 `-u` 指定测试端点

### 配置示例

```bash
# ✅ 正确：无 IP 源，使用 CloudflareSpeedTest 默认
cdnbestip -d example.com -p cf -s 2 -n

# ✅ 正确：CF IP + 自动 CF 测试端点
cdnbestip -i cf -d example.com -p cf -s 2 -n

# ✅ 正确：GCore IP + 自动 GCore 测试端点
cdnbestip -i gc -d example.com -p gc -s 2 -n

# ✅ 正确：GCore IP + 自定义测试端点
cdnbestip -i gc -u https://custom.example.com/test -d example.com -p gc -s 2 -n

# ❌ 错误：CloudFront 需要 -u 参数
cdnbestip -i ct -d example.com -p ct -s 2 -n

# ✅ 正确：CloudFront IP + 自定义测试端点
cdnbestip -i ct -u https://test.cloudfront.net/file -d example.com -p ct -s 2 -n
```

### 错误处理

当配置不正确时，工具会显示清晰的错误信息：

```bash
$ cdnbestip -i ct -d example.com -p ct -s 2 -n
❌ 配置错误：IP source 'ct' requires a custom test URL
建议：Use -u/--url option to specify test URL for CT (e.g., -u https://example.com/test)
```

## 使用示例

### 1. 基本速度测试

运行速度测试而不更新DNS：

```bash
cdnbestip -d example.com -p cf -s 2
```

这将：
- 下载CloudFlare IP列表
- 运行速度阈值为2 MB/s的速度测试
- 将结果保存到`result.csv`
- 显示性能摘要

### 2. 速度测试 + DNS更新

运行速度测试并更新DNS记录：

```bash
# 使用邮箱
cdnbestip -a user@example.com -k api_key -d example.com -p cf -s 2 -n
```

这将：
- 运行上述速度测试
- 创建/更新DNS记录，如`cf1.example.com`、`cf2.example.com`等
- 使用满足2 MB/s速度阈值的IP

### 3. 单记录更新

仅使用最快的IP更新一条DNS记录：

```bash
cdnbestip -d example.com -p cf -s 2 -n -o
```

这只会创建/更新`cf.example.com`，使用最快的IP。

### 4. 不同的IP源

#### 无IP源（使用默认设置）
```bash
cdnbestip -d example.com -p cf -s 2 -n
```

#### CloudFlare IP源（自动配置）
```bash
cdnbestip -d example.com -p cf -s 2 -n -i cf
```

#### GCore IP源（自动配置）
```bash
cdnbestip -d example.com -p gc -s 2 -n -i gc
```

#### GCore IP源（自定义测试URL）
```bash
cdnbestip -d example.com -p gc -s 2 -n -i gc -u https://hk2-speedtest.tools.gcore.com/speedtest-backend/garbage.php?ckSize=100
```

#### AWS CloudFront（需要自定义URL）
```bash
cdnbestip -d example.com -p ct -s 2 -n -i ct -u https://d1.awsstatic.com/test-file.bin
```

#### 自定义IP源（需要自定义URL）
```bash
cdnbestip -d example.com -p custom -s 2 -n -i https://example.com/custom-ips.txt -u https://test.example.com/speedtest
```

### 5. 高级配置

#### 高性能要求
```bash
cdnbestip -d example.com -p cf -s 10 -n -q 3 -P 443
```
- 仅使用速度达到10+ MB/s的IP
- 最多3条DNS记录
- 在端口443上测试

#### 使用自定义URL强制刷新
```bash
cdnbestip -d example.com -p cf -s 2 -n -r -u https://speed.cloudflare.com/__down?bytes=50000000
```
- 强制刷新缓存结果
- 使用50MB测试文件

#### 中国优化设置
```bash
export CDN="https://fastfile.asfd.cn/"
cdnbestip -d example.com -p cf -s 2 -n -c https://fastfile.asfd.cn/
```

#### 扩展参数使用
`-e/--extend` 参数允许你向 CloudflareSpeedTest 二进制文件传递额外的参数：

```bash
# 指定数据中心位置
cdnbestip -d example.com -p cf -e="-cfcolo HKG" -s 2 -n

# 多个参数（使用引号包围）
cdnbestip -d example.com -p cf -e "\-cfcolo HKG -a 1 -b 2" -s 2 -n

# 使用等号语法（推荐）
cdnbestip -d example.com -p cf -e="-tl 200 -tll 40" -s 2 -n

# 使用代理服务器
cdnbestip -d example.com -p cf --proxy http://proxy.example.com:8080 -s 2 -n
```

**注意事项：**
- 当参数以 `-` 开头时，必须使用 `-e="参数"` 或 `-e "\参数"` 格式
- 推荐使用等号语法 `-e="参数"` 避免解析问题
- 多个参数用空格分隔，整体用引号包围

### 代理配置

工具支持通过代理服务器进行网络请求，包括：
- Cloudflare API 调用（DNS 记录管理）
- IP 列表下载（从各种 CDN 提供商获取 IP 地址）

**支持的代理类型：**
- HTTP 代理：`http://proxy.example.com:8080`
- HTTPS 代理：`https://proxy.example.com:8080`

**使用方式：**

```bash
# 命令行参数
cdnbestip --proxy http://proxy.example.com:8080 -d example.com -p cf -s 2 -n

# 环境变量
export CDNBESTIP_PROXY="http://proxy.example.com:8080"
cdnbestip -d example.com -p cf -s 2 -n

# 带认证的代理
cdnbestip --proxy http://username:password@proxy.example.com:8080 -d example.com -p cf -s 2 -n

# 使用短参数
cdnbestip -x http://proxy.example.com:8080 -d example.com -p cf -s 2 -n
```

**重要说明：**
- 代理仅用于 Cloudflare API 调用和 IP 列表下载
- CloudflareSpeedTest 工具的测速过程不使用代理，确保测速结果的准确性
- 支持用户名密码认证的代理服务器
- 使用代理时，IP 列表下载将直接访问原始 URL，不使用 CDN 加速功能

## 配置文件

### 环境变量

在项目目录中创建一个`.env`文件：

```bash
# CloudFlare认证
CLOUDFLARE_API_TOKEN=your_api_token_here
# 或
CLOUDFLARE_EMAIL=your_email@example.com
CLOUDFLARE_API_KEY=your_api_key_here

# 可选：CDN加速
CDN=https://fastfile.asfd.cn/

# 可选：代理配置
CDNBESTIP_PROXY=http://proxy.example.com:8080
```

### Shell配置

添加到您的`.bashrc`或`.zshrc`：

```bash
# CloudFlare凭证
export CLOUDFLARE_API_TOKEN="your_token"

# 常用操作的别名
alias cdnbestip-test="cdnbestip -d yourdomain.com -p cf -s 2"
alias cdnbestip-update="cdnbestip -d yourdomain.com -p cf -s 2 -n"
alias cdnbestip-fast="cdnbestip -d yourdomain.com -p cf -s 5 -n -o"
```

## 输出和结果

### 控制台输出

该工具提供详细的进度信息：

```
📋 工作流步骤：
  1. 准备IP数据源
  2. 运行速度测试
  3. 处理结果
  4. 更新DNS记录

📊 步骤1：准备IP数据源...
  📥 从源下载IP列表：cf
  ✓ IP文件就绪，包含1234个IP地址

⚡ 步骤2：运行速度测试...
  🔧 确保CloudflareSpeedTest二进制文件可用...
  ✓ 二进制文件就绪：/home/user/.cdnbestip/bin/cfst
  🏃 执行速度测试...
  ✓ 速度测试完成：result.csv

📈 步骤3：处理结果...
  📄 从result.csv解析结果
  ✓ 已解析156个结果
  ✓ 89个结果超过2.0 MB/s阈值

🌐 步骤4：更新DNS记录...
  🔐 使用CloudFlare API进行认证...
  ✓ 认证成功
  📝 使用前缀更新批量DNS记录：cf
  ✓ 已更新5条DNS记录
```

### 结果文件

#### `result.csv`
包含速度测试结果：
```csv
IP,Port,Data Center,Region,City,Speed (MB/s),Latency (ms)
104.18.31.111,443,SJC,California,San Jose,6.36,169.69
103.21.244.82,443,LAX,California,Los Angeles,4.63,182.95
```

#### `ip_list.txt`
包含用于测试的IP地址/范围：
```
173.245.48.0/20
103.21.244.0/22
103.22.200.0/22
```

## 错误处理

### 常见错误和解决方案

#### 认证错误
```
❌ 配置错误：DNS操作需要CloudFlare凭证
```
**解决方案**：设置`CLOUDFLARE_API_TOKEN`或同时设置`CLOUDFLARE_API_KEY`和`CLOUDFLARE_EMAIL`

#### 域名未找到
```
❌ DNS错误：未找到域名：example.com
```
**解决方案**：确保域名已添加到您的CloudFlare账户中

#### 速度测试二进制文件问题
```
❌ 速度测试失败：未找到速度测试二进制文件
```
**解决方案**：该工具将自动下载二进制文件。检查网络连接和防火墙设置。

#### 没有结果满足阈值
```
⚠️ 没有结果满足5.0 MB/s的速度阈值
```
**解决方案**：使用`-s`降低速度阈值或尝试不同的IP源

### 调试模式

对于故障排除，您可以检查中间文件：
- `result.csv` - 速度测试结果
- `ip_list.txt` - 测试的IP地址
- `~/.cdnbestip/bin/` - 下载的二进制文件
- `~/.cdnbestip/cache/` - 缓存的IP列表

## 集成示例

### Cron任务设置

添加到crontab以实现自动更新：

```bash
# 每6小时运行一次
0 */6 * * * /usr/local/bin/cdnbestip -d example.com -p cf -s 2 -n -r >> /var/log/cdnbestip.log 2>&1

# 每天凌晨4:15运行
15 4 * * * cd /home/user && /usr/local/bin/cdnbestip -d example.com -p cf -s 2 -n -r
```

### Shell脚本集成

```bash
#!/bin/bash
# update-dns.sh

set -e

DOMAIN="example.com"
PREFIX="cf"
SPEED_THRESHOLD="2"

echo "开始为$DOMAIN优化DNS..."

if cdnbestip -d "$DOMAIN" -p "$PREFIX" -s "$SPEED_THRESHOLD" -n -r; then
    echo "DNS更新成功完成"
    # 发送通知
    curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
         -d "chat_id=$CHAT_ID" \
         -d "text=$DOMAIN的DNS优化已完成"
else
    echo "DNS更新失败"
    exit 1
fi
```

### Python脚本集成

```python
#!/usr/bin/env python3
import subprocess
import sys
import os

def update_dns(domain, prefix, speed_threshold=2.0):
    """使用CDNBESTIP工具更新DNS"""
    cmd = [
        "cdnbestip",
        "-d", domain,
        "-p", prefix,
        "-s", str(speed_threshold),
        "-n", "-r"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"{domain}的DNS更新成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"DNS更新失败：{e.stderr}")
        return False

if __name__ == "__main__":
    domains = ["example1.com", "example2.com"]
    
    for domain in domains:
        update_dns(domain, "cf", 2.0)
```

## 性能优化

### 获得更好结果的技巧

1. **选择适当的速度阈值**：从2 MB/s开始，根据您的需求进行调整
2. **使用区域性IP源**：对于亚太地区，尝试使用香港端点的GCore
3. **测试不同的端口**：某些网络在端口80上比443表现更好
4. **限制DNS记录数量**：使用`-q 3`避免过多的DNS记录
5. **缓存结果**：除非必要，否则不要使用`-r`以避免重复下载

### 监控和告警

设置监控以跟踪DNS优化：

```bash
# 检查DNS记录是否正常工作
dig cf1.example.com +short

# 监控速度测试结果
tail -f result.csv

# 检查CloudFlare API速率限制
curl -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
     "https://api.cloudflare.com/client/v4/user" | jq '.success'
```
