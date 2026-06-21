"""
报告生成模块
"""
import os
from datetime import datetime
from typing import List, Dict
from config import OUTPUT_DIR


class ReportGenerator:
    """扫描报告生成器"""

    def __init__(self, output_dir: str = OUTPUT_DIR):
        """
        初始化报告生成器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_report(self,
                       scan_results: List[Dict],
                       scan_start_time: datetime,
                       scan_type: str = "auto") -> str:
        """
        生成扫描报告

        Args:
            scan_results: 扫描结果列表
            scan_start_time: 扫描开始时间
            scan_type: 扫描类型 (user/org/auto)

        Returns:
            报告文件路径
        """
        report_time = datetime.now()
        timestamp = report_time.strftime("%Y%m%d_%H%M%S")
        filename = f"scan_report_{timestamp}.txt"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            # 写入报告头
            f.write("╔" + "═" * 78 + "╗\n")
            f.write("║" + " " * 78 + "║\n")
            f.write("║" + "          🔒 InCloud GitHub 云上扫描器 - AI API Key 扫描报告".ljust(78) + "║\n")
            f.write("║" + " " * 78 + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            # 扫描耗时
            duration = (report_time - scan_start_time).total_seconds()
            duration_str = f"{int(duration // 60)}分{int(duration % 60)}秒" if duration >= 60 else f"{int(duration)}秒"

            # 写入扫描信息
            f.write("📋 扫描信息\n")
            f.write("━" * 80 + "\n")
            f.write(f"  🎯 扫描类型:     {self._format_scan_type(scan_type)}\n")
            f.write(f"  ⏱️  开始时间:     {scan_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  ⏱️  结束时间:     {report_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  ⏳ 扫描耗时:     {duration_str}\n")

            # 快速总览
            high_count = sum(1 for r in scan_results if r.get('confidence') == 'high')
            medium_count = sum(1 for r in scan_results if r.get('confidence') == 'medium')
            repos_count = len(set(r.get('repo_url') for r in scan_results)) if scan_results else 0

            status_emoji = "🔴" if high_count > 0 else "🟡" if medium_count > 0 else "✅"
            f.write(f"  {status_emoji} 发现问题数:   {len(scan_results)} 个")
            if len(scan_results) > 0:
                f.write(f" (🔴 {high_count} 高危, 🟡 {medium_count} 中危)")
            f.write("\n")
            f.write(f"  📦 涉及仓库数:   {repos_count} 个\n")
            f.write("\n")

            # 如果没有发现问题
            if not scan_results:
                f.write("✅ 未发现敏感信息泄露！\n")
                f.write("\n扫描完成，一切正常。\n")
            else:
                # 按仓库分组
                results_by_repo = self._group_by_repo(scan_results)

                # 写入每个仓库的发现
                for repo_url, findings in results_by_repo.items():
                    self._write_repo_findings(f, repo_url, findings)

                # 写入统计信息
                self._write_statistics(f, scan_results)

            # 写入报告尾
            f.write("\n╔" + "═" * 78 + "╗\n")
            f.write("║" + " " * 78 + "║\n")
            f.write("║" + "                 ✅ 报告生成完成 - 请及时处理发现的问题".ljust(78) + "║\n")
            f.write("║" + " " * 78 + "║\n")
            f.write("║" + f"  生成时间: {report_time.strftime('%Y年%m月%d日 %H:%M:%S')}".ljust(78) + "║\n")
            f.write("║" + f"  报告位置: {filepath}".ljust(78) + "║\n")
            f.write("║" + " " * 78 + "║\n")
            f.write("╚" + "═" * 78 + "╝\n")

        return filepath

    def _group_by_repo(self, scan_results: List[Dict]) -> Dict[str, List[Dict]]:
        """
        按仓库分组扫描结果

        Args:
            scan_results: 扫描结果列表

        Returns:
            按仓库分组的结果字典
        """
        grouped = {}
        for result in scan_results:
            repo_url = result.get('repo_url', 'Unknown')
            if repo_url not in grouped:
                grouped[repo_url] = []
            grouped[repo_url].append(result)
        return grouped

    def _format_scan_type(self, scan_type: str) -> str:
        """格式化扫描类型显示"""
        type_map = {
            'auto:ai-projects': '🤖 自动搜索 AI 项目',
            'user': '👤 指定用户扫描',
            'org': '🏢 指定组织扫描',
            'single': '📦 单个仓库扫描',
        }
        for key, value in type_map.items():
            if scan_type.startswith(key):
                return value
        return scan_type

    def _write_repo_findings(self, f, repo_url: str, findings: List[Dict]):
        """
        写入单个仓库的发现

        Args:
            f: 文件对象
            repo_url: 仓库URL
            findings: 该仓库的发现列表
        """
        # 提取仓库名
        repo_name = repo_url.split('/')[-2:] if '/' in repo_url else [repo_url]
        repo_name = '/'.join(repo_name) if len(repo_name) == 2 else repo_url

        # 计算风险等级
        high_count = sum(1 for f in findings if f.get('confidence') == 'high')
        risk_level = "🔴 高危" if high_count > 0 else "🟡 中危"

        f.write("\n╭" + "─" * 78 + "╮\n")
        f.write(f"│ 📦 仓库: {repo_name}".ljust(80) + "│\n")
        f.write(f"│ 🔗 地址: {repo_url}".ljust(80) + "│\n")
        f.write(f"│ {risk_level}  发现 {len(findings)} 个问题".ljust(80) + "│\n")
        f.write("╰" + "─" * 78 + "╯\n\n")

        for idx, finding in enumerate(findings, 1):
            # 置信度标记
            confidence = finding.get('confidence', 'unknown')
            confidence_info = {
                'high': ('🔴', '高危', '立即处理'),
                'medium': ('🟡', '中危', '尽快处理'),
                'low': ('🟢', '低危', '建议处理')
            }.get(confidence, ('⚪', '未知', '需要确认'))

            f.write(f"  ┌─ 问题 #{idx} {'─' * 66}\n")
            f.write(f"  │\n")
            f.write(f"  │ {confidence_info[0]} 风险等级: {confidence_info[1]} - {confidence_info[2]}\n")
            f.write(f"  │\n")

            # 文件信息
            file_path = finding.get('file_path', 'N/A')
            f.write(f"  │ 📄 文件路径: {file_path}\n")

            # 行号
            if finding.get('line_number'):
                f.write(f"  │ 📍 行号: {finding['line_number']}\n")

            # 发现的密钥
            secret = finding.get('secret', '')
            masked_secret = self._mask_secret(secret)
            secret_type = self._identify_secret_type(secret)
            f.write(f"  │\n")
            f.write(f"  │ 🔑 密钥类型: {secret_type}\n")
            f.write(f"  │ 🔐 密钥内容: {masked_secret}\n")

            # ===== 新增：SK 密钥分析信息 =====
            sk_analysis = finding.get('sk_analysis')
            if sk_analysis:
                providers = sk_analysis.get('providers', [])
                base_urls = sk_analysis.get('base_urls', [])
                models = sk_analysis.get('models', [])

                if providers:
                    f.write(f"  │\n")
                    f.write(f"  │ 🏢 推断服务商: {', '.join(providers)}\n")
                if base_urls:
                    f.write(f"  │ 🌐 推断 Base URL:\n")
                    for url in base_urls:
                        f.write(f"  │    {url}\n")
                if models:
                    f.write(f"  │ 🤖 推断可用模型:\n")
                    for model in models[:5]:  # 最多显示5个
                        f.write(f"  │    • {model}\n")
                    if len(models) > 5:
                        f.write(f"  │    ... 还有 {len(models) - 5} 个\n")

            # 匹配来源（检测规则）
            if finding.get('pattern'):
                pattern_desc = self._explain_pattern(finding['pattern'])
                f.write(f"  │ 🎯 匹配规则: {pattern_desc}\n")

            # 代码上下文
            if finding.get('line_content'):
                line_content = finding['line_content'].strip()[:80]
                f.write(f"  │\n")
                f.write(f"  │ 💻 代码片段:\n")
                f.write(f"  │    {line_content}\n")

            # 扫描时间
            if finding.get('scan_time'):
                f.write(f"  │\n")
                f.write(f"  │ 🕐 发现时间: {finding['scan_time']}\n")

            f.write(f"  │\n")
            f.write(f"  └{'─' * 74}\n\n")

        f.write("\n")

    def _identify_secret_type(self, secret: str) -> str:
        """
        识别密钥类型

        Args:
            secret: 密钥字符串

        Returns:
            密钥类型描述
        """
        if secret.startswith('sk-proj-'):
            return '🤖 OpenAI API Key (Project)'
        elif secret.startswith('sk-ant-'):
            return '🤖 Anthropic API Key (Claude)'
        elif secret.startswith('sk-'):
            return '🤖 OpenAI API Key'
        elif secret.startswith('AIza'):
            return '🔍 Google AI API Key (Gemini)'
        elif 'openai' in secret.lower():
            return '🤖 OpenAI 相关密钥'
        elif 'anthropic' in secret.lower() or 'claude' in secret.lower():
            return '🤖 Anthropic 相关密钥'
        elif 'api_key' in secret.lower() or 'apikey' in secret.lower():
            return '🔑 通用 API Key'
        else:
            return '🔐 未知类型密钥'

    def _explain_pattern(self, pattern: str) -> str:
        """
        将正则表达式模式转换为易读的描述

        Args:
            pattern: 正则表达式字符串

        Returns:
            易读的模式描述
        """
        # 特定格式的密钥
        if 'sk-proj-' in pattern:
            return '📌 OpenAI Project API Key 格式 (sk-proj-...)'
        elif 'sk-ant-' in pattern:
            return '📌 Anthropic Claude API Key 格式 (sk-ant-...)'
        elif pattern == r'sk-[a-zA-Z0-9]{32,}':
            return '📌 OpenAI API Key 格式 (sk-...)'
        elif 'AIza' in pattern:
            return '📌 Google AI/Gemini API Key 格式 (AIza...)'

        # 环境变量模式
        elif 'OPENAI_API_KEY' in pattern:
            return '📌 OPENAI_API_KEY 环境变量赋值'
        elif 'AI_API_KEY' in pattern and 'OPENAI' not in pattern:
            return '📌 AI_API_KEY 环境变量赋值'
        elif 'ANTHROPIC_AUTH_TOKEN' in pattern:
            return '📌 ANTHROPIC_AUTH_TOKEN 环境变量赋值'
        elif 'ANTHROPIC_API_KEY' in pattern:
            return '📌 ANTHROPIC_API_KEY 环境变量赋值'
        elif 'CLAUDE_API_KEY' in pattern:
            return '📌 CLAUDE_API_KEY 环境变量赋值'
        elif 'CHAT_API_KEY' in pattern:
            return '📌 CHAT_API_KEY 环境变量赋值'
        elif 'GOOGLE_API_KEY' in pattern:
            return '📌 GOOGLE_API_KEY 环境变量赋值'
        elif 'GEMINI_API_KEY' in pattern:
            return '📌 GEMINI_API_KEY 环境变量赋值'
        elif 'AZURE_OPENAI' in pattern:
            return '📌 Azure OpenAI 环境变量赋值'
        elif 'HUGGINGFACE_API_KEY' in pattern:
            return '📌 HUGGINGFACE_API_KEY 环境变量赋值'
        elif 'HF_TOKEN' in pattern:
            return '📌 HF_TOKEN 环境变量赋值'
        elif 'COHERE_API_KEY' in pattern:
            return '📌 COHERE_API_KEY 环境变量赋值'
        elif 'API_KEY' in pattern and 'api_key' in pattern:
            return '📌 API_KEY/api_key 环境变量赋值'

        # camelCase/PascalCase 模式
        elif 'apiKey' in pattern and 'chat' not in pattern.lower() and 'openai' not in pattern.lower():
            return '📌 apiKey 对象属性/变量赋值'
        elif 'chatApiKey' in pattern:
            return '📌 chatApiKey 对象属性/变量赋值'
        elif 'openaiApiKey' in pattern or 'openAIKey' in pattern:
            return '📌 openaiApiKey/openAIKey 对象属性/变量赋值'
        elif 'anthropicApiKey' in pattern:
            return '📌 anthropicApiKey 对象属性/变量赋值'

        # 通用模式
        elif 'api_key' in pattern.lower():
            return '📌 通用 api_key 变量赋值'

        # 默认
        else:
            return f'📌 正则模式: {pattern[:50]}...' if len(pattern) > 50 else f'📌 正则模式: {pattern}'

    def _mask_secret(self, secret: str) -> str:
        """
        部分隐藏密钥

        Args:
            secret: 原始密钥

        Returns:
            隐藏后的密钥
        """
        if len(secret) <= 8:
            return "*" * len(secret)

        # 显示前4个和后4个字符
        return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"

    def _write_statistics(self, f, scan_results: List[Dict]):
        """
        写入统计信息

        Args:
            f: 文件对象
            scan_results: 扫描结果列表
        """
        f.write("\n╔" + "═" * 78 + "╗\n")
        f.write("║" + " " * 78 + "║\n")
        f.write("║" + "                           📊 统计信息与分析".ljust(78) + "║\n")
        f.write("║" + " " * 78 + "║\n")
        f.write("╚" + "═" * 78 + "╝\n\n")

        # 按置信度统计
        confidence_counts = {
            'high': 0,
            'medium': 0,
            'low': 0
        }

        for result in scan_results:
            confidence = result.get('confidence', 'low')
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

        f.write("┌─ 风险等级分布\n")
        f.write("│\n")
        total = len(scan_results)
        high_pct = (confidence_counts['high'] / total * 100) if total > 0 else 0
        medium_pct = (confidence_counts['medium'] / total * 100) if total > 0 else 0
        low_pct = (confidence_counts['low'] / total * 100) if total > 0 else 0

        f.write(f"│  🔴 高危问题: {confidence_counts['high']:3d} 个 ({high_pct:5.1f}%)")
        f.write(f"  {'█' * int(high_pct / 5)}\n")
        f.write(f"│  🟡 中危问题: {confidence_counts['medium']:3d} 个 ({medium_pct:5.1f}%)")
        f.write(f"  {'█' * int(medium_pct / 5)}\n")
        f.write(f"│  🟢 低危问题: {confidence_counts['low']:3d} 个 ({low_pct:5.1f}%)")
        f.write(f"  {'█' * int(low_pct / 5)}\n")
        f.write("│\n")
        f.write(f"│  📊 总计: {total} 个潜在问题\n")
        f.write("└" + "─" * 78 + "\n\n")

        # 按仓库统计
        repos = set(r.get('repo_url') for r in scan_results)
        f.write("┌─ 影响范围\n")
        f.write("│\n")
        f.write(f"│  📦 涉及仓库: {len(repos)} 个\n")
        f.write(f"│  📄 涉及文件: {len(set(r.get('file_path') for r in scan_results))} 个\n")
        f.write("│\n")
        f.write("└" + "─" * 78 + "\n\n")

        # 按密钥类型统计
        secret_types = {}
        for result in scan_results:
            secret = result.get('secret', '')
            stype = self._identify_secret_type(secret)
            secret_types[stype] = secret_types.get(stype, 0) + 1

        if secret_types:
            f.write("┌─ 密钥类型分布\n")
            f.write("│\n")
            for stype, count in sorted(secret_types.items(), key=lambda x: x[1], reverse=True):
                f.write(f"│  {stype}: {count} 个\n")
            f.write("│\n")
            f.write("└" + "─" * 78 + "\n\n")

        # ===== 新增：SK 密钥分析统计 =====
        sk_analyses = [r for r in scan_results if 'sk_analysis' in r]
        if sk_analyses:
            f.write("┌─ SK 密钥分析摘要\n")
            f.write("│\n")

            # 统计服务商分布
            provider_counts = {}
            for r in sk_analyses:
                analysis = r['sk_analysis']
                for p in analysis.get('providers', []):
                    provider_counts[p] = provider_counts.get(p, 0) + 1

            if provider_counts:
                f.write("│  🏢 推断服务商分布:\n")
                for p, count in sorted(provider_counts.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"│    • {p}: {count} 个密钥\n")

            # 统计 Base URL 分布
            url_counts = {}
            for r in sk_analyses:
                analysis = r['sk_analysis']
                for url in analysis.get('base_urls', []):
                    url_counts[url] = url_counts.get(url, 0) + 1

            if url_counts:
                f.write("│\n")
                f.write("│  🌐 推断 Base URL 分布:\n")
                for url, count in sorted(url_counts.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"│    • {url}: {count} 个密钥\n")

            f.write("│\n")
            f.write("└" + "─" * 78 + "\n\n")

        # 安全建议
        f.write("╔" + "═" * 78 + "╗\n")
        f.write("║" + "                           🛡️  安全建议".ljust(78) + "║\n")
        f.write("╚" + "═" * 78 + "╝\n\n")

        f.write("⚠️  立即行动（针对高危问题）：\n")
        f.write("  1. 🚨 立即撤销/轮换所有泄露的 API 密钥\n")
        f.write("  2. 🔍 检查 API 使用日志，确认是否被滥用\n")
        f.write("  3. 🗑️  从 Git 历史中彻底删除敏感信息（使用 git-filter-repo）\n")
        f.write("  4. 📧 通知相关团队成员\n\n")

        f.write("🔒 长期防护措施：\n")
        f.write("  1. 📝 使用环境变量或密钥管理服务（如 AWS Secrets Manager）\n")
        f.write("  2. 🚫 在 .gitignore 中添加 .env, config.json 等敏感文件\n")
        f.write("  3. 🪝 配置 pre-commit hooks 防止敏感信息提交\n")
        f.write("  4. 🔄 定期轮换 API 密钥\n")
        f.write("  5. 👥 对团队进行安全培训\n")
        f.write("  6. 📊 定期运行此扫描工具进行审查\n\n")

        f.write("📚 参考资源：\n")
        f.write("  • GitHub 密钥扫描: https://docs.github.com/cn/code-security/secret-scanning\n")
        f.write("  • Git 历史清理: https://github.com/newren/git-filter-repo\n")
        f.write("  • 最佳实践: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html\n")

    def generate_summary(self, report_path: str, total_findings: int) -> str:
        """
        生成简要摘要

        Args:
            report_path: 报告文件路径
            total_findings: 发现的问题总数

        Returns:
            摘要文本
        """
        if total_findings > 0:
            summary = f"""
{'━' * 80}
✅ 扫描完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 报告已保存至: {report_path}

⚠️  发现 {total_findings} 个潜在安全问题！

🔴 建议立即：
   1. 查看详细报告
   2. 撤销泄露的 API 密钥
   3. 检查是否被滥用
   4. 从 Git 历史中删除敏感信息

{'━' * 80}
"""
        else:
            summary = f"""
{'━' * 80}
✅ 扫描完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 报告已保存至: {report_path}

🎉 未发现明显的 API 密钥泄露！

💡 建议：
   • 继续保持良好的安全实践
   • 定期运行扫描检查
   • 对团队进行安全培训

{'━' * 80}
"""
        return summary
