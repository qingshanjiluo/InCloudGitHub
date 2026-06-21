"""
主扫描器模块 - 整合所有功能
"""
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable
from github_scanner import GitHubScanner
from secret_detector import SecretDetector
from report_generator import ReportGenerator
from scan_history import ScanHistory
from sk_analyzer import SKAnalyzer


class CloudScanner:
    """云上扫描器 - 主要扫描逻辑"""

    def __init__(self, github_token: str, skip_scanned: bool = True,
                 timeout_minutes: int = 50, prefer_new: bool = True):
        """
        初始化扫描器

        Args:
            github_token: GitHub Personal Access Token
            skip_scanned: 是否跳过已扫描的仓库 (默认: True)
            timeout_minutes: 扫描超时时间（分钟），默认50分钟
            prefer_new: 是否优先扫描新仓库（未扫描过的优先）(默认: True)
        """
        self.github_scanner = GitHubScanner(github_token)
        self.secret_detector = SecretDetector()
        self.report_generator = ReportGenerator()
        self.scan_history = ScanHistory()
        self.sk_analyzer = SKAnalyzer()
        self.skip_scanned = skip_scanned
        self.prefer_new = prefer_new
        self.timeout_seconds = timeout_minutes * 60
        self.scan_start_time = None

    def _is_timeout(self) -> bool:
        """检查是否超时"""
        if self.scan_start_time is None:
            return False
        elapsed = time.time() - self.scan_start_time
        return elapsed >= self.timeout_seconds

    def _check_timeout(self, current_idx: int, total_repos: int) -> bool:
        """
        检查是否超时，如果超时则打印信息并返回True

        Args:
            current_idx: 当前扫描的仓库索引
            total_repos: 总仓库数

        Returns:
            是否超时
        """
        if self._is_timeout():
            elapsed_minutes = (time.time() - self.scan_start_time) / 60
            print(f"\n⏰ 扫描超时（已运行 {elapsed_minutes:.1f} 分钟）")
            print(f"✅ 已完成 {current_idx}/{total_repos} 个仓库的扫描")
            print(f"💾 已保存前面的扫描数据，剩余 {total_repos - current_idx} 个仓库将在下次扫描时处理")
            return True
        return False

    def scan_user(self, username: str, sort_by: str = "updated") -> str:
        """
        扫描指定用户的所有公开仓库

        Args:
            username: GitHub用户名
            sort_by: 排序方式 ('updated', 'name', 'stars')

        Returns:
            报告文件路径
        """
        print(f"🚀 开始扫描用户: {username}")
        scan_start_time = datetime.now()
        self.scan_start_time = time.time()  # 开始计时

        # 获取用户的所有仓库
        repos = self.github_scanner.get_user_repos(username)
        print(f"📦 找到 {len(repos)} 个公开仓库")

        # 优先扫描新仓库
        if self.prefer_new:
            repos_to_scan = self.scan_history.get_priority_repos(
                repos, max_count=len(repos), prefer_new=True
            )
            skipped_count = len(repos) - len(repos_to_scan)
            if skipped_count > 0:
                print(f"⏭️  跳过 {skipped_count} 个已扫描的仓库")
                print(f"📦 需要扫描 {len(repos_to_scan)} 个新仓库")
        else:
            repos_to_scan, skipped_count = self._filter_scanned_repos(repos)
            if skipped_count > 0:
                print(f"⏭️  跳过 {skipped_count} 个已扫描的仓库")
                print(f"📦 需要扫描 {len(repos_to_scan)} 个新仓库")

        # 按更新时间排序（最新的优先）
        if sort_by == "updated":
            repos_to_scan.sort(
                key=lambda r: r.get('updated_at') or datetime.min,
                reverse=True
            )

        # 扫描所有仓库
        all_findings = []
        for idx, repo in enumerate(repos_to_scan, 1):
            # 检查超时
            if self._check_timeout(idx - 1, len(repos_to_scan)):
                break

            print(f"🔍 [{idx}/{len(repos_to_scan)}] 扫描仓库: {repo['full_name']}")
            findings = self._scan_repository(repo, scan_type=f"user:{username}")
            all_findings.extend(findings)

        # 生成报告
        print(f"\n📝 生成报告...")
        report_path = self.report_generator.generate_report(
            all_findings,
            scan_start_time,
            scan_type=f"user:{username}"
        )

        # 生成密钥报告（完整密钥，不脱敏）
        keys_report_path = self.report_generator.generate_keys_report(
            all_findings,
            scan_start_time,
            scan_type=f"user:{username}"
        )
        print(f"🔑 密钥报告已保存至: {keys_report_path}")

        # 打印摘要
        summary = self.report_generator.generate_summary(report_path, len(all_findings))
        print(summary)

        return report_path

    def scan_organization(self, org_name: str, sort_by: str = "updated") -> str:
        """
        扫描指定组织的所有公开仓库

        Args:
            org_name: GitHub组织名
            sort_by: 排序方式

        Returns:
            报告文件路径
        """
        print(f"🚀 开始扫描组织: {org_name}")
        scan_start_time = datetime.now()
        self.scan_start_time = time.time()  # 开始计时

        # 获取组织的所有仓库
        repos = self.github_scanner.get_org_repos(org_name)
        print(f"📦 找到 {len(repos)} 个公开仓库")

        # 优先扫描新仓库
        if self.prefer_new:
            repos_to_scan = self.scan_history.get_priority_repos(
                repos, max_count=len(repos), prefer_new=True
            )
            skipped_count = len(repos) - len(repos_to_scan)
            if skipped_count > 0:
                print(f"⏭️  跳过 {skipped_count} 个已扫描的仓库")
                print(f"📦 需要扫描 {len(repos_to_scan)} 个新仓库")
        else:
            repos_to_scan, skipped_count = self._filter_scanned_repos(repos)
            if skipped_count > 0:
                print(f"⏭️  跳过 {skipped_count} 个已扫描的仓库")
                print(f"📦 需要扫描 {len(repos_to_scan)} 个新仓库")

        # 按更新时间排序
        if sort_by == "updated":
            repos_to_scan.sort(
                key=lambda r: r.get('updated_at') or datetime.min,
                reverse=True
            )

        # 扫描所有仓库
        all_findings = []
        for idx, repo in enumerate(repos_to_scan, 1):
            # 检查超时
            if self._check_timeout(idx - 1, len(repos_to_scan)):
                break

            print(f"🔍 [{idx}/{len(repos_to_scan)}] 扫描仓库: {repo['full_name']}")
            findings = self._scan_repository(repo, scan_type=f"org:{org_name}")
            all_findings.extend(findings)

        # 生成报告
        print(f"\n📝 生成报告...")
        report_path = self.report_generator.generate_report(
            all_findings,
            scan_start_time,
            scan_type=f"org:{org_name}"
        )

        # 生成密钥报告（完整密钥，不脱敏）
        keys_report_path = self.report_generator.generate_keys_report(
            all_findings,
            scan_start_time,
            scan_type=f"org:{org_name}"
        )
        print(f"🔑 密钥报告已保存至: {keys_report_path}")

        # 打印摘要
        summary = self.report_generator.generate_summary(report_path, len(all_findings))
        print(summary)

        return report_path

    def scan_ai_projects(self, max_repos: int = 50, sort_by: str = "updated") -> str:
        """
        自动搜索并扫描AI相关项目

        Args:
            max_repos: 最大扫描仓库数
            sort_by: 排序方式 ('updated', 'stars', 'best_match')

        Returns:
            报告文件路径
        """
        print(f"🚀 开始自动搜索 AI 相关项目")
        print(f"🎯 目标: 找到并扫描 {max_repos} 个未扫描的仓库")
        scan_start_time = datetime.now()
        self.scan_start_time = time.time()  # 开始计时

        # 定义过滤函数：检查仓库是否已扫描
        def is_scanned(repo_full_name: str) -> bool:
            return self.scan_history.is_scanned(repo_full_name)

        # 搜索仓库，实时过滤已扫描的，优先新仓库
        repos_to_scan = self.github_scanner.search_ai_repos(
            max_repos=max_repos,
            skip_filter=is_scanned if self.skip_scanned else None,
            prefer_new=self.prefer_new,
            sort_by=sort_by
        )

        print(f"📦 找到 {len(repos_to_scan)} 个待扫描的仓库")

        # 扫描所有仓库
        all_findings = []
        for idx, repo in enumerate(repos_to_scan, 1):
            # 检查超时
            if self._check_timeout(idx - 1, len(repos_to_scan)):
                break

            print(f"🔍 [{idx}/{len(repos_to_scan)}] 扫描仓库: {repo['full_name']}")
            findings = self._scan_repository(repo, scan_type="auto:ai-projects")
            all_findings.extend(findings)

        # 生成报告
        print(f"\n📝 生成报告...")
        report_path = self.report_generator.generate_report(
            all_findings,
            scan_start_time,
            scan_type="auto:ai-projects"
        )

        # 生成密钥报告（完整密钥，不脱敏）
        keys_report_path = self.report_generator.generate_keys_report(
            all_findings,
            scan_start_time,
            scan_type="auto:ai-projects"
        )
        print(f"🔑 密钥报告已保存至: {keys_report_path}")

        # 打印摘要
        summary = self.report_generator.generate_summary(report_path, len(all_findings))
        print(summary)

        return report_path

    def scan_single_repo(self, repo_full_name: str) -> str:
        """
        扫描单个仓库

        Args:
            repo_full_name: 仓库全名 (owner/repo)

        Returns:
            报告文件路径
        """
        print(f"🚀 开始扫描仓库: {repo_full_name}")
        scan_start_time = datetime.now()

        # 获取仓库详细信息
        repo_info = self.github_scanner.get_repo_info(repo_full_name)
        if repo_info is None:
            # 如果获取失败，使用基本信息
            repo_info = {
                'full_name': repo_full_name,
                'url': f"https://github.com/{repo_full_name}",
                'clone_url': f"https://github.com/{repo_full_name}.git",
            }

        # 扫描仓库
        findings = self._scan_repository(repo_info)

        # 生成报告
        print(f"\n📝 生成报告...")
        report_path = self.report_generator.generate_report(
            findings,
            scan_start_time,
            scan_type=f"single:{repo_full_name}"
        )

        # 生成密钥报告（完整密钥，不脱敏）
        keys_report_path = self.report_generator.generate_keys_report(
            findings,
            scan_start_time,
            scan_type=f"single:{repo_full_name}"
        )
        print(f"🔑 密钥报告已保存至: {keys_report_path}")

        # 打印摘要
        summary = self.report_generator.generate_summary(report_path, len(findings))
        print(summary)

        return report_path

    def _filter_scanned_repos(self, repos: List[Dict]) -> tuple:
        """
        过滤已扫描的仓库

        Args:
            repos: 仓库列表

        Returns:
            (需要扫描的仓库列表, 跳过的仓库数量)
        """
        if not self.skip_scanned:
            return repos, 0

        repos_to_scan = []
        skipped_count = 0

        for repo in repos:
            repo_name = repo.get('full_name', '')
            if self.scan_history.is_scanned(repo_name):
                skipped_count += 1
            else:
                repos_to_scan.append(repo)

        return repos_to_scan, skipped_count

    def _scan_repository(self, repo: Dict, scan_type: str = "unknown") -> List[Dict]:
        """
        扫描单个仓库

        Args:
            repo: 仓库信息字典
            scan_type: 扫描类型

        Returns:
            发现的敏感信息列表
        """
        findings = []
        scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        repo_name = repo.get('full_name', 'unknown')

        try:
            # 获取仓库文件列表
            files = self.github_scanner.get_repo_files(repo['full_name'])

            # 如果获取文件列表失败（例如403错误），直接返回
            if not files:
                # 记录到扫描历史，避免下次再扫
                self.scan_history.mark_as_scanned(repo_name, 0, f"{scan_type}:no-access")
                return findings

            # 扫描每个文件
            for file_info in files:
                # 检查是否应该扫描该文件
                if not self.secret_detector.should_scan_file(file_info['path']):
                    continue

                # 获取文件内容
                content = self.github_scanner.get_file_content(
                    repo['full_name'],
                    file_info['path']
                )

                if content:
                    # 检测敏感信息
                    secrets = self.secret_detector.detect_secrets_in_text(
                        content,
                        file_info['path']
                    )

                    # 添加仓库信息
                    for secret in secrets:
                        secret['repo_url'] = repo.get('url', f"https://github.com/{repo_name}")
                        secret['repo_name'] = repo['full_name']
                        secret['scan_time'] = scan_time

                        # ===== 新增：SK密钥自动分析 =====
                        secret_value = secret.get('secret', '')
                        if secret_value.startswith('sk-') or secret_value.startswith('AIza'):
                            # 获取上下文行（前后各5行）
                            context_lines = []
                            if 'line_content' in secret:
                                context_lines.append(secret['line_content'])

                            # 综合分析密钥
                            analysis = SKAnalyzer.analyze_secret_comprehensive(
                                secret_value,
                                context_lines=context_lines,
                                file_content=content
                            )
                            secret['sk_analysis'] = analysis

                        findings.append(secret)

            # 去重和过滤
            findings = self.secret_detector.deduplicate_findings(findings)
            findings = self.secret_detector.filter_high_confidence(findings)

            if findings:
                print(f"  ⚠️  发现 {len(findings)} 个潜在问题")
                # 显示SK密钥分析摘要
                for f in findings:
                    if 'sk_analysis' in f:
                        analysis = f['sk_analysis']
                        providers = analysis.get('providers', [])
                        base_urls = analysis.get('base_urls', [])
                        models = analysis.get('models', [])
                        if providers:
                            print(f"    🔑 密钥类型: {', '.join(providers)}")
                        if base_urls:
                            print(f"    🌐 Base URL: {', '.join(base_urls[:2])}")
                        if models:
                            print(f"    🤖 可用模型: {', '.join(models[:3])}")
            else:
                print(f"  ✅ 未发现明显问题")

            # 记录到扫描历史
            self.scan_history.mark_as_scanned(repo_name, len(findings), scan_type)

        except Exception as e:
            error_msg = str(e)
            # 403错误静默处理
            if "403" in error_msg or "Forbidden" in error_msg:
                print(f"  ⏭️  跳过: 无权访问")
                self.scan_history.mark_as_scanned(repo_name, 0, f"{scan_type}:forbidden")
            else:
                print(f"  ❌ 扫描失败: {e}")
                # 即使扫描失败，也记录以避免反复尝试
                self.scan_history.mark_as_scanned(repo_name, 0, f"{scan_type}:failed")

        return findings

    def print_scan_history_summary(self):
        """打印扫描历史摘要"""
        self.scan_history.print_statistics()

    def get_scan_history_summary(self) -> str:
        """获取扫描历史摘要文本"""
        return self.scan_history.get_scan_summary_text()
