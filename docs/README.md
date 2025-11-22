# CDNBestIP 文档

本目录包含 CDNBestIP 项目的完整文档，使用 [MkDocs](https://www.mkdocs.org/) 和 [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) 主题构建。

## 本地预览

### 安装依赖

```bash
pip install mkdocs-material
pip install mkdocs-git-revision-date-localized-plugin
pip install mkdocs-minify-plugin
pip install mkdocs-redirects
```

或使用 uv：

```bash
uv pip install mkdocs-material mkdocs-git-revision-date-localized-plugin mkdocs-minify-plugin mkdocs-redirects
```

### 启动开发服务器

```bash
mkdocs serve
```

然后在浏览器中访问 http://127.0.0.1:8000

### 构建静态文件

```bash
mkdocs build
```

构建的文件将输出到 `site/` 目录。

## 文档结构

```
docs/
├── index.md                    # 首页
├── getting-started/            # 快速开始
│   ├── installation.md         # 安装指南
│   └── quickstart.md           # 快速入门
├── user-guide/                 # 用户指南
│   ├── cli-reference.md        # 命令行参考
│   ├── ip-sources.md           # IP 数据源
│   ├── dns-management.md       # DNS 管理
│   ├── configuration.md        # 配置文件
│   └── advanced-usage.md       # 高级用法
├── deployment/                 # 部署指南
│   ├── docker.md               # Docker 部署
│   ├── cron-jobs.md            # 定时任务
│   └── kubernetes.md           # Kubernetes
├── development/                # 开发文档
│   ├── contributing.md         # 贡献指南
│   └── api-reference.md        # API 参考
├── faq.md                      # 常见问题
├── changelog.md                # 更新日志
└── stylesheets/                # 自定义样式
    └── extra.css
```

## 编写指南

### Markdown 扩展

文档支持以下 Markdown 扩展：

#### 代码块

\`\`\`python
def hello_world():
    print("Hello, World!")
\`\`\`

#### 标签页

=== "Python"

    \`\`\`python
    print("Hello")
    \`\`\`

=== "Bash"

    \`\`\`bash
    echo "Hello"
    \`\`\`

#### 提示框

!!! note "注意"
    这是一个注意事项。

!!! tip "提示"
    这是一个提示。

!!! warning "警告"
    这是一个警告。

!!! danger "危险"
    这是一个危险警告。

#### 表格

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 值1 | 值2 | 值3 |

#### 任务列表

- [x] 已完成的任务
- [ ] 未完成的任务

### 样式指南

1. **标题层级**：使用 `#` 到 `####`，不要跳级
2. **代码块**：始终指定语言
3. **链接**：使用相对路径链接其他文档
4. **图片**：放在 `docs/images/` 目录
5. **中英文混排**：中英文之间加空格

### 提交指南

1. 确保文档可以正常构建：`mkdocs build --strict`
2. 检查链接是否有效
3. 预览效果：`mkdocs serve`
4. 提交前运行拼写检查

## 自动部署

文档通过 GitHub Actions 自动部署到 GitHub Pages。

### 工作流程

1. 推送到 `main` 分支
2. GitHub Actions 自动触发
3. 构建文档
4. 部署到 `gh-pages` 分支
5. 可通过 https://idev-sig.github.io/cdnbestip/ 访问

### 手动部署

```bash
mkdocs gh-deploy --force
```

## 贡献

欢迎贡献文档！请参阅 [贡献指南](development/contributing.md)。

### 文档改进建议

- 修正错别字和语法错误
- 添加更多示例
- 改进现有说明
- 添加新的指南
- 翻译文档

## 许可证

文档采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 许可证。
