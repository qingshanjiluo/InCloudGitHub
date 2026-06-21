"""
扫描历史管理模块 - 跟踪已扫描的仓库，避免重复扫描，支持优先级排序
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path


class ScanHistory:
    """扫描历史管理器"""

    def __init__(self, history_file: str = None):
        """
        初始化扫描历史管理器

        Args:
            history_file: 历史记录文件路径，默认为 scan_history/scanned_repos.json
        """
        if history_file is None:
            history_dir = Path("scan_history")
            history_dir.mkdir(exist_ok=True)
            self.history_file = history_dir / "scanned_repos.json"
        else:
            self.history_file = Path(history_file)
            self.history_file.parent.mkdir(exist_ok=True, parents=True)

        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """
        从文件加载扫描历史

        Returns:
            历史记录字典
        """
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  加载扫描历史失败: {e}，将创建新历史记录")
                return {"repos": {}, "total_scanned": 0, "last_updated": None}
        else:
            return {"repos": {}, "total_scanned": 0, "last_updated": None}

    def _save_history(self):
        """保存扫描历史到文件"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  保存扫描历史失败: {e}")

    def is_scanned(self, repo_full_name: str) -> bool:
        """
        检查仓库是否已经被扫描过

        Args:
            repo_full_name: 仓库全名 (owner/repo)

        Returns:
            True 如果已扫描，False 如果未扫描
        """
        return repo_full_name in self.history["repos"]

    def get_scan_info(self, repo_full_name: str) -> Optional[Dict]:
        """
        获取仓库的扫描信息

        Args:
            repo_full_name: 仓库全名 (owner/repo)

        Returns:
            扫描信息字典，如果未扫描过则返回 None
        """
        return self.history["repos"].get(repo_full_name)

    def mark_as_scanned(self, repo_full_name: str, findings_count: int = 0,
                        scan_type: str = "unknown"):
        """
        标记仓库为已扫描

        Args:
            repo_full_name: 仓库全名 (owner/repo)
            findings_count: 发现的问题数量
            scan_type: 扫描类型
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        existing = self.history["repos"].get(repo_full_name, {})

        self.history["repos"][repo_full_name] = {
            "first_scan": existing.get("first_scan", now),
            "last_scan": now,
            "findings_count": findings_count,
            "scan_type": scan_type,
            "scan_count": existing.get("scan_count", 0) + 1,
            # 保留之前的发现总数（累计）
            "total_findings": existing.get("total_findings", 0) + findings_count,
            # 标记是否有发现
            "has_findings": existing.get("has_findings", False) or (findings_count > 0),
        }

        self.history["total_scanned"] = len(self.history["repos"])
        self.history["last_updated"] = now

        self._save_history()

    def get_scanned_repos(self) -> List[str]:
        """
        获取所有已扫描的仓库列表

        Returns:
            仓库全名列表
        """
        return list(self.history["repos"].keys())

    def get_scanned_count(self) -> int:
        """
        获取已扫描的仓库总数

        Returns:
            仓库数量
        """
        return self.history["total_scanned"]

    def clear_history(self):
        """清空扫描历史"""
        self.history = {"repos": {}, "total_scanned": 0, "last_updated": None}
        self._save_history()
        print("✅ 扫描历史已清空")

    def remove_repo(self, repo_full_name: str):
        """
        从历史记录中移除指定仓库

        Args:
            repo_full_name: 仓库全名 (owner/repo)
        """
        if repo_full_name in self.history["repos"]:
            del self.history["repos"][repo_full_name]
            self.history["total_scanned"] = len(self.history["repos"])
            self.history["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_history()
            print(f"✅ 已从历史记录中移除: {repo_full_name}")
        else:
            print(f"⚠️  仓库不在历史记录中: {repo_full_name}")

    def get_statistics(self) -> Dict:
        """
        获取扫描统计信息

        Returns:
            统计信息字典
        """
        total_findings = sum(
            repo_info.get("findings_count", 0)
            for repo_info in self.history["repos"].values()
        )

        repos_with_findings = sum(
            1 for repo_info in self.history["repos"].values()
            if repo_info.get("has_findings", False) or repo_info.get("findings_count", 0) > 0
        )

        # 统计扫描失败的仓库
        failed_repos = sum(
            1 for repo_info in self.history["repos"].values()
            if "failed" in repo_info.get("scan_type", "") or "forbidden" in repo_info.get("scan_type", "")
        )

        # 统计无权限访问的仓库
        no_access_repos = sum(
            1 for repo_info in self.history["repos"].values()
            if "no-access" in repo_info.get("scan_type", "")
        )

        return {
            "total_scanned": self.history["total_scanned"],
            "total_findings": total_findings,
            "repos_with_findings": repos_with_findings,
            "failed_repos": failed_repos,
            "no_access_repos": no_access_repos,
            "last_updated": self.history["last_updated"],
        }

    def print_statistics(self):
        """打印扫描统计信息"""
        stats = self.get_statistics()
        print(f"\n📊 扫描历史统计:")
        print(f"   总扫描仓库数: {stats['total_scanned']}")
        print(f"   发现问题总数: {stats['total_findings']}")
        print(f"   有问题的仓库: {stats['repos_with_findings']}")
        print(f"   扫描失败的仓库: {stats['failed_repos']}")
        print(f"   无权限访问的仓库: {stats['no_access_repos']}")
        if stats['last_updated']:
            print(f"   最后更新时间: {stats['last_updated']}")

    # ========== 新增：优先级和排序功能 ==========

    def get_unscanned_repos_sorted(self, repos: List[Dict],
                                   sort_by: str = "updated_at",
                                   reverse: bool = True) -> List[Dict]:
        """
        从未扫描的仓库中按指定规则排序返回

        Args:
            repos: 仓库列表（每个仓库是包含 full_name 等信息的字典）
            sort_by: 排序字段，如 'updated_at', 'pushed_at', 'created_at', 'name'
            reverse: 是否降序（True=最新的优先）

        Returns:
            排序后的未扫描仓库列表
        """
        unscanned = [r for r in repos if not self.is_scanned(r.get('full_name', ''))]

        if sort_by in ('updated_at', 'pushed_at', 'created_at'):
            # 时间字段排序
            def sort_key(repo):
                val = repo.get(sort_by)
                if val is None:
                    return datetime.min if reverse else datetime.max
                if isinstance(val, str):
                    try:
                        return datetime.strptime(val, '%Y-%m-%dT%H:%M:%SZ')
                    except ValueError:
                        return datetime.min
                return val  # datetime 对象
            unscanned.sort(key=sort_key, reverse=reverse)
        elif sort_by == 'name':
            unscanned.sort(key=lambda r: r.get('full_name', '').lower(), reverse=reverse)
        elif sort_by == 'stars':
            unscanned.sort(key=lambda r: r.get('stargazers_count', 0), reverse=reverse)

        return unscanned

    def get_priority_repos(self, repos: List[Dict],
                           max_count: int = 50,
                           prefer_new: bool = True,
                           min_stars: int = 0) -> List[Dict]:
        """
        获取优先扫描的仓库列表（新仓库优先）

        Args:
            repos: 仓库列表
            max_count: 最大返回数量
            prefer_new: 是否优先扫描新仓库（未扫描过的）
            min_stars: 最低 star 数过滤

        Returns:
            优先扫描的仓库列表
        """
        if min_stars > 0:
            repos = [r for r in repos if r.get('stargazers_count', 0) >= min_stars]

        if not prefer_new:
            return repos[:max_count]

        # 分离已扫描和未扫描
        scanned = [r for r in repos if self.is_scanned(r.get('full_name', ''))]
        unscanned = [r for r in repos if not self.is_scanned(r.get('full_name', ''))]

        # 未扫描的按更新时间排序（最新的优先）
        unscanned.sort(
            key=lambda r: r.get('updated_at') or datetime.min,
            reverse=True
        )

        # 已扫描的也按更新时间排序
        scanned.sort(
            key=lambda r: r.get('updated_at') or datetime.min,
            reverse=True
        )

        # 优先返回未扫描的，如果不够再补已扫描的
        result = unscanned[:max_count]
        if len(result) < max_count:
            result.extend(scanned[:max_count - len(result)])

        return result

    def get_repos_need_rescan(self, days_threshold: int = 7) -> List[str]:
        """
        获取需要重新扫描的仓库（超过指定天数未扫描）

        Args:
            days_threshold: 天数阈值

        Returns:
            需要重新扫描的仓库全名列表
        """
        now = datetime.now()
        need_rescan = []

        for repo_name, info in self.history["repos"].items():
            last_scan_str = info.get("last_scan", "")
            if not last_scan_str:
                continue
            try:
                last_scan = datetime.strptime(last_scan_str, '%Y-%m-%d %H:%M:%S')
                days_diff = (now - last_scan).days
                if days_diff >= days_threshold:
                    need_rescan.append(repo_name)
            except ValueError:
                continue

        return need_rescan

    def get_repos_with_findings(self) -> List[Tuple[str, int]]:
        """
        获取发现问题的仓库列表（按发现数降序）

        Returns:
            [(仓库名, 发现数), ...]
        """
        repos = []
        for repo_name, info in self.history["repos"].items():
            count = info.get("findings_count", 0)
            if count > 0:
                repos.append((repo_name, count))

        repos.sort(key=lambda x: x[1], reverse=True)
        return repos

    def get_scan_summary_text(self) -> str:
        """生成扫描历史摘要文本"""
        stats = self.get_statistics()
        lines = [
            "📊 扫描历史摘要",
            "━" * 40,
            f"  总扫描仓库数: {stats['total_scanned']}",
            f"  发现问题总数: {stats['total_findings']}",
            f"  有问题的仓库: {stats['repos_with_findings']}",
            f"  扫描失败的仓库: {stats['failed_repos']}",
            f"  无权限访问的仓库: {stats['no_access_repos']}",
        ]
        if stats['last_updated']:
            lines.append(f"  最后更新时间: {stats['last_updated']}")

        # 显示发现问题的仓库
        repos_with_findings = self.get_repos_with_findings()
        if repos_with_findings:
            lines.append("")
            lines.append("  ⚠️  发现问题的仓库（Top 10）:")
            for repo_name, count in repos_with_findings[:10]:
                lines.append(f"    • {repo_name}: {count} 个发现")

        return "\n".join(lines)
