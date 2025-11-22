# 快速入门

本指南将帮助你快速开始使用 CDNBestIP。

## 前提条件

在开始之前，确保你已经：

1. ✅ 安装了 CDNBestIP（参见 [安装指南](installation.md)）
2. ✅ 拥有 CloudFlare 账号
3. ✅ 获取了 API 令牌或 API 密钥

## 获取 CloudFlare 凭证

### 方法 1: API 令牌 (推荐)

1. 登录 [CloudFlare Dashboard](https://dash.cloudflare.com/)
2. 进入 **My Profile** → **API Tokens**
3. 点击 **Create Token**
4. 选择 **Edit zone DNS** 模板
5. 配置权限并创建令牌
6. 复制生成的令牌

### 方法 2: API 密钥

1. 登录 [CloudFlare Dashboard](https://dash.cloudflare.com/)
2. 进入 **My Profile** → **API Tokens**
3. 在 **API Keys** 部分，查看 **Global API Key**
4. 点击 **View** 并复制密钥

## 第一次运行

### 1. 仅运行速度测试

最简单的用法是只运行速度测试，不更新 DNS：

```bash
cdnbestip -d example.com -p cf -s 2
```

这将：

- 下载 CloudFlare IP 列表
- 运行速度测试（阈值 2 MB/s）
- 显示测试结果
- 保存结果到 `result.csv`

### 2. 测试并更新 DNS

使用 API 令牌更新 DNS 记录：

```bash
cdnbestip -t YOUR_API_TOKEN -d example.com -p cf -s 2 -n
```

或使用 API 密钥 + 邮箱：

```bash
cdnbestip -a your@email.com -k YOUR_API_KEY -d example.com -p cf -s 2 -n
```

这将：

- 运行速度测试
- 创建/更新 DNS 记录（如 `cf1.example.com`, `cf2.example.com`）
- 使用满足速度阈值的最佳 IP

### 3. 只更新一条记录

如果只想使用最快的 IP：

```bash
cdnbestip -t YOUR_API_TOKEN -d example.com -p cf -s 2 -n -o
```

这将只创建/更新 `cf.example.com` 记录。

## 使用环境变量

为了避免每次都输入凭证，可以设置环境变量：

=== "Linux/macOS"

    ```bash
    # 添加到 ~/.bashrc 或 ~/.zshrc
    export CLOUDFLARE_API_TOKEN="your_token_here"
    
    # 或使用 API 密钥
    export CLOUDFLARE_EMAIL="your@email.com"
    export CLOUDFLARE_API_KEY="your_key_here"
    ```

=== "Windows (PowerShell)"

    ```powershell
    # 临时设置
    $env:CLOUDFLARE_API_TOKEN="your_token_here"
    
    # 永久设置
    [System.Environment]::SetEnvironmentVariable('CLOUDFLARE_API_TOKEN', 'your_token_here', 'User')
    ```

=== "Windows (CMD)"

    ```cmd
    setx CLOUDFLARE_API_TOKEN "your_token_here"
    ```

设置后，可以简化命令：

```bash
cdnbestip -d example.com -p cf -s 2 -n
```

## 常用场景

### 场景 1: 优化网站 CDN

```bash
# 测试 CloudFlare IP 并更新前 3 条最快的记录
cdnbestip -d example.com -p cf -s 5 -n -q 3
```

### 场景 2: 使用不同的 IP 源

```bash
# 使用 GCore IP（自动配置测试端点）
cdnbestip -d example.com -p gc -s 3 -n -i gc

# 使用 CloudFront IP（需要指定测试 URL）
cdnbestip -d example.com -p ct -s 3 -n -i ct -u https://test.cloudfront.net/file
```

### 场景 3: 强制刷新结果

```bash
# 忽略缓存，重新测试
cdnbestip -d example.com -p cf -s 2 -n -r
```

### 场景 4: 调试模式

```bash
# 启用详细日志
cdnbestip -d example.com -p cf -s 2 -n --debug
```

## 理解输出

运行命令后，你会看到类似的输出：

```
CDNBESTIP Configuration Summary:
==================================================

📋 Authentication:
  ✓ Method: API Token

🌐 DNS Settings:
  ✓ Domain: example.com
  ✓ Prefix: cf
  ✓ Record Type: A

⚡ Speed Test Settings:
  ✓ Speed Threshold: 2.0 MB/s
  ✓ Record Limit: Unlimited

📊 IP Data Source:
  ✓ Source: CloudFlare

⚙️ Operations:
  ✓ Update DNS (multiple records)

==================================================

🚀 Starting CDNBESTIP workflow...

📋 Workflow Steps:
  1. Prepare IP data source
  2. Run speed test
  3. Process results
  4. Update DNS records

📊 Step 1: Preparing IP data source...
  📥 Downloading IP list from source: cf
  ✓ IP file ready: ip_list_cf.txt with 1234 IP addresses

⚡ Step 2: Running speed test...
  🔧 Ensuring CloudflareSpeedTest binary is available...
  ✓ Binary ready: /home/user/.cdnbestip/bin/cfst
  🏃 Executing speed test...
  ✓ Speed test completed: result.csv

📈 Step 3: Processing results...
  📄 Parsing results from: result.csv
  ✓ Parsed 156 results
  ✓ 89 results above 2.0 MB/s threshold
  ✓ Selected top 5 results

🌐 Step 4: Updating DNS records...
  🔐 Validating CloudFlare credentials...
  ✅ CloudFlare credentials validated successfully
  📝 Updating batch DNS records with prefix: cf
  ✓ Updated 5 DNS records:
    • cf1.example.com → 104.18.31.111
    • cf2.example.com → 103.21.244.82
    • cf3.example.com → 172.64.155.23
    • cf4.example.com → 104.16.132.229
    • cf5.example.com → 172.67.74.226

✅ Workflow completed successfully!
```

## 检查结果

### 查看 DNS 记录

```bash
# 使用 dig
dig cf1.example.com +short

# 使用 nslookup
nslookup cf1.example.com

# 使用 host
host cf1.example.com
```

### 查看结果文件

```bash
# 查看速度测试结果
cat result.csv

# 查看 IP 列表
cat ip_list_cf.txt
```

## 下一步

现在你已经了解了基本用法，可以：

- 📖 阅读 [命令行参数参考](../user-guide/cli-reference.md) 了解所有选项
- 🐳 尝试 [Docker 部署](../deployment/docker.md) 实现自动化
- ❓ 查看 [常见问题](../faq.md) 解决疑问

## 常见问题

### Q: 为什么没有找到满足阈值的 IP？

A: 尝试降低速度阈值（`-s` 参数）或使用不同的 IP 源。

### Q: 如何只测试不更新 DNS？

A: 不使用 `-n` 参数即可：

```bash
cdnbestip -d example.com -p cf -s 2
```

### Q: 如何查看详细的调试信息？

A: 使用 `--debug` 或 `-D` 参数：

```bash
cdnbestip -d example.com -p cf -s 2 -n --debug
```

### Q: 结果保存在哪里？

A: 
- 速度测试结果：`result.csv`
- IP 列表：`ip_list_cf.txt`（根据 IP 源不同而不同）
- 日志文件：`~/.cdnbestip/logs/`
- 缓存文件：`~/.cdnbestip/cache/`
