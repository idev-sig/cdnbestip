# 更新日志

本页面记录 CDNBestIP 的所有重要更改。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2024-11-22

### 新增
- 🚀 首次发布
- ✨ 基于 CloudflareSpeedTest 的自动化测速
- 🌐 CloudFlare DNS 记录自动更新
- 📊 支持多个 IP 数据源（CloudFlare、GCore、CloudFront、AWS）
- 🎯 智能 IP 源配置（自动配置测试端点）
- 🔧 完整的命令行界面
- 🐳 Docker 支持
- 📝 详细的日志记录系统
- 🔒 支持 API 令牌和 API 密钥认证
- ⚡ 结果缓存机制
- 🌍 跨平台支持（Windows、Linux、macOS）
- 🔄 代理服务器支持
- 📖 完整的文档

### 功能特性

#### 核心功能
- 自动下载和管理 CloudflareSpeedTest 二进制文件
- 支持多种 DNS 记录类型（A、AAAA、CNAME 等）
- 灵活的速度阈值配置
- DNS 记录数量限制
- 强制刷新选项
- 单记录更新模式

#### IP 数据源
- CloudFlare IP 自动配置
- GCore IP 自动配置
- CloudFront IP 支持（需手动配置）
- AWS IP 支持（需手动配置）
- 自定义 IP 列表支持

#### 高级功能
- 扩展参数传递给 CloudflareSpeedTest
- CDN 加速支持
- 代理服务器支持（HTTP/HTTPS）
- 多级日志系统
- 性能监控和统计
- 错误处理和恢复

#### 部署支持
- Docker 镜像
- Docker Compose 配置
- Kubernetes 支持
- 定时任务集成
- 环境变量配置

### 文档
- 完整的用户指南
- API 参考文档
- 部署指南
- 常见问题解答
- 贡献指南

### 已知问题
- 无

## 版本说明

### 版本号规则

版本号格式：`主版本号.次版本号.修订号`

- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

### 更新类型

- **新增 (Added)**：新功能
- **变更 (Changed)**：现有功能的变更
- **弃用 (Deprecated)**：即将移除的功能
- **移除 (Removed)**：已移除的功能
- **修复 (Fixed)**：Bug 修复
- **安全 (Security)**：安全相关的修复

## 贡献

感谢所有为 CDNBestIP 做出贡献的开发者！

### 主要贡献者

- [@jetsung](https://github.com/jetsung) - 项目创建者和维护者

## 支持

如果你有任何问题：

1. 查看 [常见问题](faq.md)
2. 搜索 [GitHub Issues](https://github.com/idev-sig/cdnbestip/issues)
3. 提交新的 [Issue](https://github.com/idev-sig/cdnbestip/issues/new)

---

[0.1.0]: https://github.com/idev-sig/cdnbestip/releases/tag/v0.1.0
