# 🔍 AI API Key Scanner

<div align="center">

**自动扫描 GitHub 仓库，发现泄露的 AI API 密钥**

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/automation-GitHub%20Actions-2088FF.svg)](https://github.com/features/actions)

🚀 **完全基于 GitHub Actions，无需本地运行** | 💰 **公开仓库完全免费**

</div>

---

## 📖 简介

自动化安全扫描工具，发现 GitHub 仓库中泄露的 AI API 密钥（OpenAI、Anthropic Claude 等）。

### 核心特性

- ✅ **零配置运行** - Fork 后只需添加 Token
- ✅ **全自动化** - 每天自动扫描
- ✅ **智能检测** - 自动过滤示例代码，减少误报
- ✅ **详细报告** - 报告提交到仓库永久保存，同时上传 Artifacts 保留 90 天
- ✅ **即时告警** - 发现问题自动创建 Issue
- ✅ **完全免费** - 公开仓库无限使用

---

## 🚀 快速开始

### 1. Fork 本仓库

点击页面右上角的 **Fork** 按钮。

### 2. 创建 GitHub Token

1. 访问 https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**
3. 配置：
   - Note: `AI Scanner Token`
   - Expiration: `90 days` 或更长
   - Scopes: ✅ `public_repo` (必需)、✅ `read:org` (可选)
4. 生成并复制 Token（格式：`ghp_xxxxxxxxxxxx`）

### 3. 添加 Token 到仓库

1. 访问你 Fork 的仓库：`Settings` → `Secrets and variables` → `Actions`
2. 点击 **New repository secret**
3. Name: `GH_SCAN_TOKEN`（必须大小写一致）
4. Value: 粘贴你的 Token
5. 点击 **Add secret**

### 4. 启动扫描

**手动触发**（推荐首次使用）：
1. 访问 `Actions` 页面
2. 选择 **AI API Key Scanner - Manual Scan**
3. 点击 **Run workflow**
4. 配置参数：
   - Scan type: `auto - 自动搜索AI项目`
   - Max repos: `10`（首次建议少量测试）
5. 点击 **Run workflow** 开始扫描

**自动运行**：配置完成后，工作流将每天 UTC 02:00（北京时间 10:00）自动运行。

---

## 📊 查看结果

### 1. 查看仓库中的报告
扫描完成后，报告会自动提交到 `scan_reports/` 目录，可以直接在仓库中查看。

### 2. 查看运行日志
在 Actions 页面点击任意运行记录查看扫描状态和摘要。

### 3. 下载 Artifacts
运行详情页面底部 **Artifacts** 区域可下载报告副本（保留 90 天）。

### 4. 查看自动 Issue
发现问题时会自动创建带 `security` 标签的 Issue。

---

## 🎯 功能特性

### 智能检测
- 支持多种 AI API 密钥：OpenAI (`sk-...`、`sk-proj-...`)、Anthropic (`sk-ant-...`)
- 自动过滤示例代码和占位符
- 置信度评分（高/中/低）

### 详细报告
- 包含仓库地址、文件路径、行号、代码片段
- 部分隐藏密钥保护安全
- 统计分析和安全建议
- 报告保存在 `scan_reports/` 目录，提交到仓库永久保存

### 自动告警
- 发现问题自动创建 Issue
- 智能避免重复 Issue

### 灵活配置
- 4 种扫描模式：auto（自动搜索AI项目）、user（指定用户）、org（指定组织）、repo（单个仓库）
- 自定义扫描数量和时间

---

## 🛠️ 工作流说明

### Manual Scan（手动扫描）⭐ 推荐
- 触发方式：仅手动触发
- 适用场景：首次测试、按需扫描

### Auto Scan（自动扫描）
- 触发方式：每天 UTC 02:00 或手动触发
- 适用场景：日常自动监控

### Scheduled Scan（增强定时扫描）
- 触发方式：每天 UTC 02:00 或手动触发
- 适用场景：企业级定期安全审计
- 特点：详细统计分析、智能 Issue 管理、超时保护（60 分钟）

---

## ⚙️ 自定义配置

### 修改扫描时间

编辑 `.github/workflows/scheduled-scan.yml`：

```yaml
on:
  schedule:
    - cron: '0 2 * * *'      # 每天 02:00 UTC（北京时间 10:00）
    # - cron: '0 */12 * * *' # 每 12 小时
    # - cron: '0 2 * * 1'    # 每周一
```

**时区说明**：GitHub Actions 使用 UTC 时区，北京时间 = UTC + 8 小时。

### 修改扫描数量

编辑工作流文件：

```yaml
python scan_github.py --auto --max-repos 100  # 修改数字
```

### 添加自定义检测规则

编辑 `config.py`：

```python
SENSITIVE_PATTERNS = [
    r'sk-[a-zA-Z0-9]{32,}',              # OpenAI
    r'sk-ant-[a-zA-Z0-9_-]{32,}',        # Anthropic
    r'your_custom_pattern',               # 自定义规则
]
```

---

## ❓ 常见问题

**Q: 工作流没有自动运行？**
- 检查 Actions 是否启用
- 手动触发一次测试
- 确认 Cron 时间设置正确

**Q: 提示 "GitHub Token is required"？**
- 确认 Secret 名称是 `GH_SCAN_TOKEN`（大小写一致）
- 检查 Token 是否过期
- 验证 Token 有 `public_repo` 权限

**Q: API 速率限制？**
- 减少 `--max-repos` 参数
- 增加扫描间隔
- 等待 1 小时后重试

**Q: 如何停止自动扫描？**
- Actions 页面 → 选择工作流 → "..." → "Disable workflow"

---

## 🛡️ 发现泄露密钥后的处理

### 立即采取的步骤

1. **轮换密钥**：登录 API 提供商控制台，删除泄露的密钥，生成新密钥
2. **检查日志**：查看 API 调用记录，确认是否有异常使用
3. **清理 Git 历史**：使用 BFG Repo-Cleaner 或 git-filter-repo 清理
4. **更新代码实践**：

```python
# ✅ 推荐：使用环境变量
import os
api_key = os.getenv('OPENAI_API_KEY')

# ❌ 错误：硬编码密钥
api_key = "sk-proj-xxxxxxxxxxxx"
```

更新 `.gitignore`：

```gitignore
.env
.env.local
config.json
secrets.json
*.key
*.pem
```

---

## ⚠️ 免责声明

- 本工具仅用于安全研究和合法的安全审计
- 用户需对使用本工具的行为负责
- 请遵守相关法律法规和 GitHub 使用条款
- 工具可能存在误报或漏报，建议人工复核

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

<div align="center">

### 🛡️ 让你的代码更安全！

Made with ❤️ for Security

</div>
