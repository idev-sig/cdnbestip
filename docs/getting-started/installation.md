# 安装指南

本指南将帮助你在不同平台上安装 CDNBestIP。

## 系统要求

- **Python 版本**: Python 3.13 或更高
- **操作系统**: Windows, Linux, macOS
- **依赖**: CloudflareSpeedTest v2.3.4+

## 安装方法

### 方法 1: 使用 pip (推荐)

最简单的安装方式是通过 PyPI：

```bash
pip install cdnbestip
```

### 方法 2: 使用 uv

[uv](https://github.com/astral-sh/uv) 是一个快速的 Python 包管理器：

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 使用 uv 安装 cdnbestip
uv tool install cdnbestip
```

### 方法 3: 从源码安装

如果你需要最新的开发版本：

```bash
# 使用 pip
pip install git+https://github.com/idev-sig/cdnbestip.git

# 使用 uv
uv tool install git+https://github.com/idev-sig/cdnbestip.git

# 指定版本
uv tool install git+https://github.com/idev-sig/cdnbestip.git@v0.1.0
```

### 方法 4: Docker

使用 Docker 无需安装 Python 环境：

```bash
# 拉取镜像
docker pull idevsig/cdnbestip:latest

# 或从其他镜像仓库
docker pull ghcr.io/idev-sig/cdnbestip:latest
```

## 平台特定安装

### Linux

=== "Ubuntu/Debian"

    ```bash
    # 安装 Python 3.13
    sudo apt update
    sudo apt install python3.13 python3.13-pip
    
    # 安装 CDNBestIP
    pip3.13 install cdnbestip
    ```

=== "CentOS/RHEL/Fedora"

    ```bash
    # 安装 Python 3.13
    sudo dnf install python3.13 python3.13-pip
    
    # 安装 CDNBestIP
    pip3.13 install cdnbestip
    ```

=== "Arch Linux"

    ```bash
    # 安装 Python
    sudo pacman -S python python-pip
    
    # 安装 CDNBestIP
    pip install cdnbestip
    ```

### macOS

```bash
# 使用 Homebrew 安装 Python
brew install python@3.13

# 安装 CDNBestIP
pip3.13 install cdnbestip
```

### Windows

1. 从 [python.org](https://www.python.org/downloads/) 下载并安装 Python 3.13+
2. 打开命令提示符或 PowerShell
3. 运行安装命令：

```powershell
pip install cdnbestip
```

## 验证安装

安装完成后，验证是否成功：

```bash
# 检查版本
cdnbestip --version

# 查看帮助信息
cdnbestip --help
```

预期输出：

```
cdnbestip 0.1.0
```

## 升级

### 升级到最新版本

```bash
# 使用 pip
pip install --upgrade cdnbestip

# 使用 uv
uv tool upgrade cdnbestip
```

### 升级到特定版本

```bash
pip install cdnbestip==0.1.0
```

## 卸载

```bash
# 使用 pip
pip uninstall cdnbestip

# 使用 uv
uv tool uninstall cdnbestip
```

## 故障排除

### 问题 1: Python 版本不兼容

**错误信息**:
```
ERROR: Package 'cdnbestip' requires a different Python: 3.12.0 not in '>=3.13'
```

**解决方案**:
升级到 Python 3.13 或更高版本。

### 问题 2: 权限错误

**错误信息**:
```
ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied
```

**解决方案**:
使用 `--user` 标志安装到用户目录：

```bash
pip install --user cdnbestip
```

### 问题 3: 网络问题

**错误信息**:
```
ERROR: Could not find a version that satisfies the requirement cdnbestip
```

**解决方案**:
使用国内镜像源：

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple cdnbestip
```

### 问题 4: 依赖冲突

**解决方案**:
创建虚拟环境：

```bash
# 创建虚拟环境
python -m venv cdnbestip_env

# 激活虚拟环境
source cdnbestip_env/bin/activate  # Linux/macOS
cdnbestip_env\Scripts\activate     # Windows

# 安装
pip install cdnbestip
```

## 下一步

安装完成后，继续阅读 [快速入门](quickstart.md) 了解如何使用 CDNBestIP。
