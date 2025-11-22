# 命令行参数参考

本页面提供 CDNBestIP 所有命令行参数的详细说明。

## 基本语法

```bash
cdnbestip [OPTIONS]
```

## 认证选项

### CloudFlare 凭证

| 参数 | 长参数 | 类型 | 描述 |
|------|--------|------|------|
| `-a` | `--email` | string | CloudFlare 账号邮箱 |
| `-k` | `--key` | string | CloudFlare API 密钥 |
| `-t` | `--token` | string | CloudFlare API 令牌（推荐） |

!!! tip "推荐使用 API 令牌"
    API 令牌比 API 密钥更安全，因为它可以限制权限范围和有效期。

**示例：**

=== "使用 API 令牌"

    ```bash
    cdnbestip -t YOUR_API_TOKEN -d example.com -p cf -s 2 -n
    ```

=== "使用 API 密钥"

    ```bash
    cdnbestip -a your@email.com -k YOUR_API_KEY -d example.com -p cf -s 2 -n
    ```

=== "使用环境变量"

    ```bash
    export CLOUDFLARE_API_TOKEN="YOUR_TOKEN"
    cdnbestip -d example.com -p cf -s 2 -n
    ```

## DNS 设置

### 域名配置

| 参数 | 长参数 | 类型 | 必需 | 描述 |
|------|--------|------|------|------|
| `-d` | `--domain` | string | DNS 操作时必需 | 目标域名 |
| `-p` | `--prefix` | string | DNS 操作时必需 | DNS 记录前缀 |
| `-y` | `--type` | string | 否 | DNS 记录类型（默认：A） |

**支持的 DNS 记录类型：**

- `A` - IPv4 地址（默认）
- `AAAA` - IPv6 地址
- `CNAME` - 规范名称
- `MX` - 邮件交换
- `TXT` - 文本记录
- `SRV` - 服务记录
- `NS` - 名称服务器
- `PTR` - 指针记录

**示例：**

```bash
# 创建 A 记录
cdnbestip -d example.com -p cf -s 2 -n

# 创建 AAAA 记录
cdnbestip -d example.com -p cf -y AAAA -s 2 -n

# 创建 CNAME 记录
cdnbestip -d example.com -p cdn -y CNAME -s 2 -n
```

## 速度测试设置

### 测试参数

| 参数 | 长参数 | 类型 | 默认值 | 描述 |
|------|--------|------|--------|------|
| `-s` | `--speed` | float | None | 下载速度阈值（MB/s） |
| `-P` | `--port` | int | 443 | 测试端口 |
| `-u` | `--url` | string | 自动 | 测试 URL |
| `-T` | `--timeout` | int | 600 | 超时时间（秒） |
| `-q` | `--quantity` | int | 0 | DNS 记录数量限制 |

!!! info "速度阈值说明"
    - 当 `-s` 未指定或为 0 时：不传递 `-sl` 和 `-tl` 参数给 cfst，不进行速度过滤
    - 当 `-s` 大于 0 时：传递 `-sl` 和 `-tl 200` 给 cfst，同时进行速度和延迟过滤

**示例：**

```bash
# 速度阈值 5 MB/s
cdnbestip -d example.com -p cf -s 5 -n

# 自定义端口
cdnbestip -d example.com -p cf -s 2 -P 80 -n

# 限制 DNS 记录数量
cdnbestip -d example.com -p cf -s 2 -q 3 -n

# 自定义测试 URL
cdnbestip -d example.com -p cf -s 2 -u https://speed.cloudflare.com/__down?bytes=50000000 -n
```

## IP 数据源

### 数据源选项

| 参数 | 长参数 | 类型 | 描述 |
|------|--------|------|------|
| `-i` | `--ip-url` | string | IP 数据源或自定义 URL |

**预定义数据源：**

| 值 | 提供商 | 自动配置 | 推荐区域 |
|----|--------|----------|----------|
| `cf` | CloudFlare | ✅ | 全球 |
| `gc` | GCore | ✅ | 亚太 |
| `ct` | CloudFront | ❌ | 全球 |
| `aws` | Amazon AWS | ❌ | 全球 |

**示例：**

```bash
# 使用 CloudFlare IP
cdnbestip -i cf -d example.com -p cf -s 2 -n

# 使用 GCore IP
cdnbestip -i gc -d example.com -p gc -s 2 -n

# 使用 CloudFront IP（需要指定测试 URL）
cdnbestip -i ct -u https://test.cloudfront.net/file -d example.com -p ct -s 2 -n

# 使用自定义 IP 列表
cdnbestip -i https://example.com/custom-ips.txt -u https://test.example.com/file -d example.com -p custom -s 2 -n
```

## 操作标志

### 操作选项

| 参数 | 长参数 | 描述 |
|------|--------|------|
| `-r` | `--refresh` | 强制刷新 result.csv |
| `-n` | `--dns` | 更新 DNS 记录 |
| `-o` | `--only` | 仅更新一条记录（最快的 IP） |

**示例：**

```bash
# 强制刷新并测试
cdnbestip -d example.com -p cf -s 2 -r

# 测试并更新 DNS
cdnbestip -d example.com -p cf -s 2 -n

# 只更新一条最快的记录
cdnbestip -d example.com -p cf -s 2 -n -o

# 组合使用
cdnbestip -d example.com -p cf -s 2 -r -n -o
```

## 高级选项

### 扩展参数

| 参数 | 长参数 | 类型 | 描述 |
|------|--------|------|------|
| `-c` | `--cdn` | string | CDN URL（用于加速） |
| `-e` | `--extend` | string | CloudflareSpeedTest 扩展参数 |
| `-x` | `--proxy` | string | 代理服务器 URL |

**扩展参数示例：**

```bash
# 指定数据中心
cdnbestip -d example.com -p cf -e="-cfcolo HKG" -s 2 -n

# 多个参数
cdnbestip -d example.com -p cf -e "\-cfcolo HKG -a 1 -b 2" -s 2 -n

# 使用等号语法（推荐）
cdnbestip -d example.com -p cf -e="-tl 200 -tll 40" -s 2 -n
```

**代理配置示例：**

```bash
# HTTP 代理
cdnbestip -x http://proxy.example.com:8080 -d example.com -p cf -s 2 -n

# HTTPS 代理
cdnbestip -x https://proxy.example.com:8080 -d example.com -p cf -s 2 -n

# 带认证的代理
cdnbestip -x http://user:pass@proxy.example.com:8080 -d example.com -p cf -s 2 -n
```

## 日志和调试

### 日志选项

| 参数 | 长参数 | 类型 | 描述 |
|------|--------|------|------|
| `-D` | `--debug` | flag | 启用调试模式 |
| `-v` | `--verbose` | flag | 启用详细输出 |
| `-L` | `--log-level` | string | 设置日志级别 |
| `-C` | `--no-console-log` | flag | 禁用控制台日志 |
| `-F` | `--no-file-log` | flag | 禁用文件日志 |

**日志级别：**

- `DEBUG` - 调试信息
- `INFO` - 一般信息（默认）
- `WARNING` - 警告信息
- `ERROR` - 错误信息
- `CRITICAL` - 严重错误

**示例：**

```bash
# 启用调试模式
cdnbestip -d example.com -p cf -s 2 -n --debug

# 设置日志级别
cdnbestip -d example.com -p cf -s 2 -n -L DEBUG

# 禁用控制台日志
cdnbestip -d example.com -p cf -s 2 -n -C

# 仅输出到文件
cdnbestip -d example.com -p cf -s 2 -n -C
```

## 其他选项

### 帮助和版本

| 参数 | 长参数 | 描述 |
|------|--------|------|
| `-h` | `--help` | 显示帮助信息 |
| `-V` | `--version` | 显示版本信息 |

**示例：**

```bash
# 显示帮助
cdnbestip --help

# 显示版本
cdnbestip --version
```

## 环境变量

除了命令行参数，还可以使用环境变量：

| 环境变量 | 对应参数 | 描述 |
|----------|----------|------|
| `CLOUDFLARE_API_TOKEN` | `-t` | API 令牌 |
| `CLOUDFLARE_EMAIL` | `-a` | 账号邮箱 |
| `CLOUDFLARE_API_KEY` | `-k` | API 密钥 |
| `CDNBESTIP_DOMAIN` | `-d` | 域名 |
| `CDNBESTIP_PREFIX` | `-p` | DNS 前缀 |
| `CDNBESTIP_SPEED` | `-s` | 速度阈值 |
| `CDNBESTIP_PROXY` | `-x` | 代理 URL |
| `CDN` | `-c` | CDN URL |

**示例：**

```bash
# 设置环境变量
export CLOUDFLARE_API_TOKEN="your_token"
export CDNBESTIP_DOMAIN="example.com"
export CDNBESTIP_PREFIX="cf"

# 简化命令
cdnbestip -s 2 -n
```

## 完整示例

### 基本用法

```bash
# 最简单的用法
cdnbestip -d example.com -p cf -s 2

# 完整的 DNS 更新
cdnbestip -t YOUR_TOKEN -d example.com -p cf -s 5 -n -q 3

# 使用所有主要选项
cdnbestip \
  -t YOUR_TOKEN \
  -d example.com \
  -p cf \
  -s 5 \
  -P 443 \
  -q 3 \
  -i cf \
  -n \
  -r \
  --debug
```

### 高级用法

```bash
# 多区域优化
cdnbestip -i gc -d asia.example.com -p gc -s 3 -n -q 5
cdnbestip -i cf -d global.example.com -p cf -s 3 -n -q 5

# 使用代理和自定义参数
cdnbestip \
  -x http://proxy.example.com:8080 \
  -e="-cfcolo HKG -tl 200" \
  -d example.com \
  -p cf \
  -s 5 \
  -n

# 调试模式
cdnbestip \
  -d example.com \
  -p cf \
  -s 2 \
  -n \
  --debug \
  -L DEBUG \
  -v
```

## 参数优先级

当同一个配置通过多种方式指定时，优先级如下：

1. 命令行参数（最高优先级）
2. 环境变量
3. 默认值（最低优先级）

**示例：**

```bash
# 环境变量
export CDNBESTIP_SPEED="2"

# 命令行参数会覆盖环境变量
cdnbestip -d example.com -p cf -s 5 -n  # 使用 5 而不是 2
```

## 常见错误

### 缺少必需参数

```bash
# ❌ 错误：DNS 操作需要域名
cdnbestip -p cf -s 2 -n

# ✅ 正确
cdnbestip -d example.com -p cf -s 2 -n
```

### 参数冲突

```bash
# ❌ 错误：-o 需要 -n
cdnbestip -d example.com -p cf -s 2 -o

# ✅ 正确
cdnbestip -d example.com -p cf -s 2 -n -o
```

### IP 源配置错误

```bash
# ❌ 错误：CloudFront 需要测试 URL
cdnbestip -i ct -d example.com -p ct -s 2 -n

# ✅ 正确
cdnbestip -i ct -u https://test.cloudfront.net/file -d example.com -p ct -s 2 -n
```
