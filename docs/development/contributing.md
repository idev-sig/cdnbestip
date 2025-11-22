# 贡献指南

感谢你考虑为 CDNBestIP 做出贡献！本指南将帮助你了解如何参与项目开发。

## 行为准则

参与本项目即表示你同意遵守我们的行为准则：

- 尊重所有贡献者
- 接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

## 如何贡献

### 报告 Bug

在提交 Bug 报告之前：

1. 检查 [现有 Issues](https://github.com/idev-sig/cdnbestip/issues) 是否已有相同问题
2. 确保使用最新版本
3. 收集相关信息

提交 Bug 报告时，请包含：

- 清晰的标题和描述
- 重现步骤
- 预期行为和实际行为
- 系统信息（OS、Python 版本等）
- 相关日志和错误信息

**Bug 报告模板：**

```markdown
**描述问题**
简要描述问题。

**重现步骤**
1. 执行命令 '...'
2. 查看输出 '...'
3. 看到错误

**预期行为**
描述你期望发生什么。

**实际行为**
描述实际发生了什么。

**环境信息**
- OS: [e.g. Ubuntu 22.04]
- Python 版本: [e.g. 3.13.0]
- CDNBestIP 版本: [e.g. 0.1.0]

**日志**
```
粘贴相关日志
```

**截图**
如果适用，添加截图。
```

### 功能建议

提交功能建议时，请：

1. 检查是否已有类似建议
2. 清楚地描述功能
3. 解释为什么需要这个功能
4. 提供使用示例

**功能建议模板：**

```markdown
**功能描述**
简要描述你想要的功能。

**问题背景**
描述这个功能要解决什么问题。

**建议的解决方案**
描述你希望如何实现。

**替代方案**
描述你考虑过的其他方案。

**使用示例**
```bash
# 示例命令
cdnbestip --new-feature ...
```

**附加信息**
其他相关信息。
```

### 提交代码

#### 开发环境设置

1. Fork 仓库
2. 克隆你的 fork：

```bash
git clone https://github.com/YOUR_USERNAME/cdnbestip.git
cd cdnbestip
```

3. 安装开发依赖：

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync --group dev
```

4. 创建分支：

```bash
git checkout -b feature/your-feature-name
```

#### 代码规范

我们使用以下工具确保代码质量：

- **Black** - 代码格式化
- **Ruff** - 代码检查
- **pytest** - 测试框架
- **mypy** - 类型检查

运行检查：

```bash
# 格式化代码
uv run black src/ tests/

# 检查代码
uv run ruff check src/ tests/

# 类型检查
uv run mypy src/

# 运行测试
uv run pytest
```

#### 编码指南

**Python 代码风格：**

- 遵循 [PEP 8](https://pep8.org/)
- 使用类型提示
- 编写文档字符串
- 保持函数简短和专注
- 使用有意义的变量名

**示例：**

```python
def calculate_speed_threshold(
    results: list[SpeedTestResult],
    threshold: float
) -> list[SpeedTestResult]:
    """
    Filter results by speed threshold.
    
    Args:
        results: List of speed test results
        threshold: Minimum speed in MB/s
        
    Returns:
        Filtered list of results
        
    Raises:
        ValueError: If threshold is negative
    """
    if threshold < 0:
        raise ValueError("Threshold must be non-negative")
    
    return [r for r in results if r.speed >= threshold]
```

**提交信息规范：**

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

示例：

```
feat(cli): add proxy support for API calls

Add --proxy option to allow users to specify a proxy server
for CloudFlare API calls and IP list downloads.

Closes #123
```

#### 测试

所有新功能都应该包含测试：

```python
# tests/unit/test_new_feature.py
import pytest
from cdnbestip import new_feature

def test_new_feature_basic():
    """Test basic functionality."""
    result = new_feature.do_something()
    assert result == expected_value

def test_new_feature_edge_case():
    """Test edge case."""
    with pytest.raises(ValueError):
        new_feature.do_something(invalid_input)
```

运行测试：

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/unit/test_new_feature.py

# 运行并查看覆盖率
uv run pytest --cov=src/cdnbestip --cov-report=html
```

#### 文档

更新相关文档：

1. 代码文档字符串
2. README.md
3. docs/ 目录下的文档
4. CHANGELOG.md

#### 提交 Pull Request

1. 确保所有测试通过
2. 更新文档
3. 推送到你的 fork：

```bash
git push origin feature/your-feature-name
```

4. 在 GitHub 上创建 Pull Request
5. 填写 PR 模板
6. 等待审查

**PR 检查清单：**

- [ ] 代码遵循项目规范
- [ ] 添加了测试
- [ ] 测试全部通过
- [ ] 更新了文档
- [ ] 更新了 CHANGELOG.md
- [ ] 提交信息清晰
- [ ] 没有合并冲突

### 文档贡献

文档同样重要！你可以：

- 修正错别字和语法错误
- 改进现有说明
- 添加新的指南和示例
- 翻译文档

文档位于 `docs/` 目录，使用 MkDocs 构建。

本地预览：

```bash
pip install mkdocs-material
mkdocs serve
```

## 开发工作流

### 1. 选择任务

- 查看 [Issues](https://github.com/idev-sig/cdnbestip/issues)
- 选择标记为 `good first issue` 的任务（适合新手）
- 或提出新的功能建议

### 2. 讨论

- 在 Issue 中讨论实现方案
- 获得维护者的反馈
- 避免重复工作

### 3. 开发

- 创建分支
- 编写代码
- 添加测试
- 更新文档

### 4. 审查

- 提交 PR
- 响应审查意见
- 进行必要的修改

### 5. 合并

- PR 被批准后合并
- 删除分支
- 庆祝！🎉

## 发布流程

（仅限维护者）

1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建 Git 标签
4. 推送标签触发 CI/CD
5. 发布到 PyPI
6. 创建 GitHub Release

## 社区

### 获取帮助

- 📖 [文档](https://idev-sig.github.io/cdnbestip/)
- 💬 [Discussions](https://github.com/idev-sig/cdnbestip/discussions)
- 🐛 [Issues](https://github.com/idev-sig/cdnbestip/issues)

### 保持联系

- GitHub: [@idev-sig](https://github.com/idev-sig)
- 项目主页: [cdnbestip](https://github.com/idev-sig/cdnbestip)

## 许可证

贡献代码即表示你同意将代码以 [Apache License 2.0](https://github.com/idev-sig/cdnbestip/blob/main/LICENSE) 许可证发布。

## 致谢

感谢所有贡献者！你们的贡献让 CDNBestIP 变得更好。

### 贡献者名单

查看 [贡献者页面](https://github.com/idev-sig/cdnbestip/graphs/contributors)。

## 问题？

如有任何问题，请：

1. 查看 [FAQ](../faq.md)
2. 搜索 [Issues](https://github.com/idev-sig/cdnbestip/issues)
3. 在 [Discussions](https://github.com/idev-sig/cdnbestip/discussions) 提问
4. 联系维护者

再次感谢你的贡献！🙏
