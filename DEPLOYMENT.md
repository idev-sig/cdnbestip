# Deployment Guide

This guide covers the deployment and distribution of the CDNBESTIP Python package across different platforms and environments.

## Package Information

- **Package Name**: `cdnbestip`
- **Version**: 1.0.0
- **Python Requirements**: Python 3.13+
- **License**: Apache License 2.0
- **Repository**: https://github.com/idev-sig/cdnbestip
- **Dependencies**: CloudflareSpeedTest v2.3.4+, cloudflare>=4.3.1, requests
- **Supported Platforms**: Windows, Linux, macOS
- **Supported IP Sources**: CloudFlare, GCore, CloudFront, AWS

## Build Requirements

### Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/idev-sig/cdnbestip.git
cd cdnbestip

# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install development dependencies
uv sync --group dev
```

### Building the Package

```bash
# Build source distribution and wheel
uv build

# Output files will be in dist/:
# - cdnbestip-1.0.0.tar.gz (source distribution)
# - cdnbestip-1.0.0-py3-none-any.whl (wheel)
```

## Distribution Methods

### 1. PyPI Distribution

#### Preparation
```bash
# Install build tools
uv add --group dev twine

# Build the package
uv build

# Check the distribution
uv run twine check dist/*
```

#### Upload to PyPI
```bash
# Upload to Test PyPI first
uv run twine upload --repository testpypi dist/*

# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ cdnbestip

# Upload to production PyPI
uv run twine upload dist/*
```

### 2. GitHub Releases

#### Automated Release (GitHub Actions)
Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install 3.13
    
    - name: Build package
      run: uv build
    
    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/*
        generate_release_notes: true
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: |
        uv add twine
        uv run twine upload dist/*
```

#### Manual Release
```bash
# Create and push tag
git tag v1.0.0
git push origin v1.0.0

# Build package
uv build

# Create GitHub release manually and upload dist/* files
```

### 3. Docker Distribution

#### Multi-stage Dockerfile
```dockerfile
# Build stage
FROM python:3.13-slim as builder

WORKDIR /build
COPY . .

RUN pip install uv
RUN uv build

# Runtime stage
FROM python:3.13-slim

RUN pip install uv
COPY --from=builder /build/dist/*.whl /tmp/
RUN uv pip install --system /tmp/*.whl && rm /tmp/*.whl

ENTRYPOINT ["cdnbestip"]
```

#### Build and Push
```bash
# Build image
docker build -t idevsig/cdnbestip:1.0.0 .
docker tag idevsig/cdnbestip:1.0.0 idevsig/cdnbestip:latest

# Push to registries
docker push idevsig/cdnbestip:1.0.0
docker push idevsig/cdnbestip:latest

# Push to additional registries
docker tag idevsig/cdnbestip:1.0.0 ghcr.io/idev-sig/cdnbestip:1.0.0
docker push ghcr.io/idev-sig/cdnbestip:1.0.0
```

## Platform-Specific Deployment

### Linux/macOS

#### Manual Installation
```bash
# Install Python 3.13+
# Ubuntu/Debian
sudo apt update && sudo apt install python3.13 python3.13-pip

# CentOS/RHEL/Fedora
sudo dnf install python3.13 python3.13-pip

# macOS (using Homebrew)
brew install python@3.13

# Install CDNBESTIP
pip3.13 install cdnbestip
```

### Windows

#### Manual Installation
```powershell
# Install Python 3.13+ from python.org
# Then install CDNBESTIP
pip install cdnbestip
```

### Docker Deployment

#### Single Command
```bash
docker run --rm \
  -e CLOUDFLARE_API_TOKEN="your_token" \
  idevsig/cdnbestip:latest \
  -d example.com -p cf -s 2 -n
```

#### Docker Compose
```yaml
services:
  cdnbestip:
    image: idevsig/cdnbestip:latest
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
      - TZ=UTC
    command: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
    restart: unless-stopped
```

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cdnbestip
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cdnbestip
  template:
    metadata:
      labels:
        app: cdnbestip
    spec:
      containers:
      - name: cdnbestip
        image: idevsig/cdnbestip:1.0.0
        env:
        - name: CLOUDFLARE_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: cloudflare-secret
              key: api-token
        command: ["cdnbestip"]
        args: ["-d", "example.com", "-p", "cf", "-s", "2", "-n"]
```

## Validation and Testing

### Pre-deployment Testing

```bash
# Run deployment validation
python scripts/validate_deployment.py

# Run unit tests
uv run pytest

# Run integration tests
uv run pytest tests/integration/

# Check code quality
uv run black --check src/
uv run ruff check src/
```

### Post-deployment Verification

```bash
# Test installation from PyPI
pip install cdnbestip
cdnbestip --version
cdnbestip --help

# Test Docker image
docker run --rm idevsig/cdnbestip:latest --version

# Test functionality (with credentials)
export CLOUDFLARE_API_TOKEN="your_token"
cdnbestip -d example.com -p cf -s 2  # Speed test only
```

## IP Source Configuration for Deployment

### Automatic Configuration

The tool automatically configures test endpoints based on IP source selection:

```bash
# CloudFlare - automatic configuration
cdnbestip -i cf -d example.com -p cf -s 2 -n

# GCore - automatic configuration  
cdnbestip -i gc -d example.com -p gc -s 2 -n

# CloudFront - requires manual URL
cdnbestip -i ct -u https://test.cloudfront.net/file -d example.com -p ct -s 2 -n
```

### Deployment Validation

```bash
# Test IP source configurations
cdnbestip -i cf --help  # Should show CF as valid source
cdnbestip -i gc --help  # Should show GC as valid source

# Test automatic configuration
cdnbestip -i cf -d test.com -p cf -s 2  # Should auto-configure CF test URL
cdnbestip -i gc -d test.com -p gc -s 2  # Should auto-configure GCore test URL

# Test error handling
cdnbestip -i ct -d test.com -p ct -s 2  # Should show error requiring -u parameter
```

### Production IP Source Recommendations

```bash
# For global CDN optimization
cdnbestip -i cf -d production.com -p cf -s 5 -n -q 3

# For Asia-Pacific regions
cdnbestip -i gc -d production.com -p gc -s 5 -n -q 3

# For AWS infrastructure
cdnbestip -i ct -u https://your-cloudfront-test-url.com/test -d production.com -p ct -s 5 -n -q 3
```

## Environment-Specific Configurations

### Production Environment

```bash
# Set up production environment
export CLOUDFLARE_API_TOKEN="production_token"
export CDNBESTIP_LOG_LEVEL="INFO"
export CDNBESTIP_CACHE_DIR="/var/cache/cdnbestip"

# Run with production settings - CloudFlare IPs
cdnbestip -d production.com -p cf -s 5 -n -q 3 -i cf

# Run with production settings - GCore IPs
cdnbestip -d production.com -p gc -s 5 -n -q 3 -i gc

# Run with production settings - Custom CloudFront
cdnbestip -d production.com -p ct -s 5 -n -q 3 -i ct -u https://d1.awsstatic.com/test-file.bin
```

### Development Environment

```bash
# Set up development environment
export CLOUDFLARE_API_TOKEN="dev_token"
export CDNBESTIP_LOG_LEVEL="DEBUG"

# Run with development settings - CloudFlare IPs
cdnbestip -d dev.example.com -p cf -s 1 -n -r -i cf

# Run with development settings - GCore IPs with debug
cdnbestip -d dev.example.com -p gc -s 1 -n -r -i gc --debug

# Test different IP sources
cdnbestip -d dev.example.com -p test -s 1 -r -i gc  # Speed test only
```

### CI/CD Environment

```yaml
# GitHub Actions example
- name: Test CDNBESTIP
  env:
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
  run: |
    pip install cdnbestip
    cdnbestip -d test.example.com -p cf -s 2
```

## Monitoring and Maintenance

### Health Checks

```bash
# Basic health check
cdnbestip --version

# Functionality check
cdnbestip --help | grep -q "CloudFlare DNS" && echo "OK" || echo "FAIL"

# Dependency check
python -c "import cloudflare, requests; print('Dependencies OK')"
```

### Log Management

```bash
# Enable logging
export CDNBESTIP_LOG_LEVEL="INFO"
export CDNBESTIP_LOG_FILE="/var/log/cdnbestip.log"

# Rotate logs (using logrotate)
cat > /etc/logrotate.d/cdnbestip << EOF
/var/log/cdnbestip.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF
```

### Performance Monitoring

```bash
# Monitor execution time
time cdnbestip -d example.com -p cf -s 2 -n

# Monitor resource usage
/usr/bin/time -v cdnbestip -d example.com -p cf -s 2 -n

# Monitor API rate limits
curl -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
     "https://api.cloudflare.com/client/v4/user" | jq '.success'
```

## Common Deployment Scenarios

### Scenario 1: Multi-Region CDN Optimization

```bash
# Asia-Pacific: Use GCore for better performance
cdnbestip -i gc -d asia.example.com -p gc -s 3 -n -q 5

# Global: Use CloudFlare
cdnbestip -i cf -d global.example.com -p cf -s 3 -n -q 5

# AWS regions: Use CloudFront with custom test URL
cdnbestip -i ct -u https://test-file.s3.amazonaws.com/speedtest -d aws.example.com -p ct -s 3 -n -q 5
```

### Scenario 2: Automated Cron Jobs

```bash
# /etc/cron.d/cdnbestip-optimization
# Optimize CloudFlare IPs every 6 hours
0 */6 * * * root /usr/local/bin/cdnbestip -i cf -d example.com -p cf -s 2 -n -r -q 3 >> /var/log/cdnbestip-cf.log 2>&1

# Optimize GCore IPs daily at 2 AM
0 2 * * * root /usr/local/bin/cdnbestip -i gc -d example.com -p gc -s 2 -n -r -q 3 >> /var/log/cdnbestip-gc.log 2>&1
```

### Scenario 3: Docker Compose Multi-Source

```yaml
services:
  cdnbestip-cf:
    image: idevsig/cdnbestip:latest
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
    command: ["-i", "cf", "-d", "example.com", "-p", "cf", "-s", "2", "-n", "-q", "3"]
    restart: unless-stopped

  cdnbestip-gc:
    image: idevsig/cdnbestip:latest
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
    command: ["-i", "gc", "-d", "example.com", "-p", "gc", "-s", "2", "-n", "-q", "3"]
    restart: unless-stopped
```

### Scenario 4: Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cdnbestip-optimization
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cdnbestip
            image: idevsig/cdnbestip:latest
            env:
            - name: CLOUDFLARE_API_TOKEN
              valueFrom:
                secretKeyRef:
                  name: cloudflare-secret
                  key: api-token
            command: ["cdnbestip"]
            args: ["-i", "cf", "-d", "example.com", "-p", "cf", "-s", "2", "-n", "-r", "-q", "3"]
          restartPolicy: OnFailure
```

## Troubleshooting Deployment Issues

### Common Issues

#### IP Source Configuration Errors
```bash
# Error: IP source requires custom URL
$ cdnbestip -i ct -d example.com -p ct -s 2 -n
❌ ConfigurationError: IP source 'ct' requires a custom test URL

# Solution: Provide -u parameter
cdnbestip -i ct -u https://test-endpoint.com/file -d example.com -p ct -s 2 -n

# Error: Invalid IP source
$ cdnbestip -i invalid -d example.com -p test -s 2
❌ ValidationError: Invalid IP data URL format

# Solution: Use valid IP sources
cdnbestip -i cf -d example.com -p cf -s 2  # CloudFlare
cdnbestip -i gc -d example.com -p gc -s 2  # GCore
```

#### Test Endpoint Connectivity
```bash
# Test CloudFlare endpoint
curl -I https://cf.xiu2.xyz/url

# Test GCore endpoint
curl -I https://hk2-speedtest.tools.gcore.com/speedtest-backend/garbage.php?ckSize=1000

# Test custom endpoint
curl -I https://your-custom-test-url.com/test
```

#### Python Version Compatibility
```bash
# Check Python version
python --version
python3 --version

# Install specific Python version
pyenv install 3.13.7
pyenv global 3.13.7
```

#### Dependency Conflicts
```bash
# Create isolated environment
python -m venv cdnbestip_env
source cdnbestip_env/bin/activate  # Linux/macOS
# or
cdnbestip_env\Scripts\activate     # Windows

pip install cdnbestip
```

#### Permission Issues
```bash
# Install for user only
pip install --user cdnbestip

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

#### Network Issues
```bash
# Use alternative index
pip install -i https://pypi.org/simple/ cdnbestip

# Use proxy
pip install --proxy http://proxy.example.com:8080 cdnbestip
```

### Debug Mode

```bash
# Enable debug output
export CDNBESTIP_DEBUG=1
cdnbestip -d example.com -p cf -s 2 -n

# Verbose pip installation
pip install -v cdnbestip

# Check installation
pip show cdnbestip
pip list | grep cdnbestip
```

## Security Considerations

### API Token Security

```bash
# Use environment variables (recommended)
export CLOUDFLARE_API_TOKEN="token_here"

# Use configuration files with restricted permissions
echo "CLOUDFLARE_API_TOKEN=token_here" > ~/.cdnbestip.env
chmod 600 ~/.cdnbestip.env
```

### Container Security

```dockerfile
# Use non-root user
FROM python:3.13-slim
RUN useradd -m -u 1000 cdnbestip
USER cdnbestip
WORKDIR /home/cdnbestip
```

### Network Security

```bash
# Restrict network access (if needed)
docker run --rm \
  --network none \
  -v /etc/hosts:/etc/hosts:ro \
  idevsig/cdnbestip:latest \
  --help
```

## Rollback Procedures

### Package Rollback

```bash
# Install specific version
pip install cdnbestip==0.9.0

# Downgrade
pip install --upgrade cdnbestip==0.9.0

# Uninstall
pip uninstall cdnbestip
```

### Docker Rollback

```bash
# Use previous image version
docker pull idevsig/cdnbestip:0.9.0
docker tag idevsig/cdnbestip:0.9.0 idevsig/cdnbestip:latest

# Update deployments
kubectl set image deployment/cdnbestip cdnbestip=idevsig/cdnbestip:0.9.0
```

## Support and Documentation

- **Usage Guide**: [USAGE.md](USAGE.md)
- **Issue Tracker**: https://github.com/idev-sig/cdnbestip/issues
