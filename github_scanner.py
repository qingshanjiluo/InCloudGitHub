"""
GitHub仓库扫描模块
"""
import time
import re
from datetime import datetime
from typing import List, Dict, Optional, Callable
from github import Github, GithubException
from config import GITHUB_TOKEN, AI_SEARCH_KEYWORDS, MAX_REPOS_PER_SEARCH, SEARCH_DELAY_SECONDS


class GitHubScanner:
    """GitHub仓库扫描器"""

    def __init__(self, token: str = GITHUB_TOKEN):
        """
        初始化GitHub扫描器

        Args:
            token: GitHub Personal Access Token
        """
        if not token:
            raise ValueError("GitHub Token is required. Please set GITHUB_TOKEN in .env file")

        # 配置超时和重试参数，避免长时间等待
        self.github = Github(
            token,
            timeout=30,  # 设置30秒超时
            retry=None   # 禁用自动重试，我们自己处理
        )
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    def get_rate_limit_info(self) -> Dict:
        """获取API速率限制信息"""
        rate_limit = self.github.get_rate_limit()
        core = rate_limit.core

        return {
            'remaining': core.remaining,
            'limit': core.limit,
            'reset': core.reset
        }

    def wait_for_rate_limit(self):
        """等待速率限制重置"""
        info = self.get_rate_limit_info()
        if info['remaining'] < 10:
            # info['reset'] 是 datetime 对象，需要和 datetime.now() 比较
            wait_time = (info['reset'] - datetime.now()).total_seconds() + 10
            print(f"⚠️  API速率限制即将耗尽，等待 {wait_time:.0f} 秒...")
            time.sleep(max(0, wait_time))

    def get_user_repos(self, username: str) -> List[Dict]:
        """
        获取指定用户的所有公开仓库

        Args:
            username: GitHub用户名

        Returns:
            仓库信息列表
        """
        try:
            user = self.github.get_user(username)
            repos = []

            for repo in user.get_repos():
                if not repo.private:
                    repos.append({
                        'name': repo.name,
                        'full_name': repo.full_name,
                        'url': repo.html_url,
                        'clone_url': repo.clone_url,
                        'description': repo.description,
                        'updated_at': repo.updated_at,
                        'pushed_at': repo.pushed_at,
                        'created_at': repo.created_at,
                        'stargazers_count': repo.stargazers_count,
                        'language': repo.language,
                    })

            return repos
        except GithubException as e:
            print(f"❌ 获取用户仓库失败: {e}")
            return []

    def get_org_repos(self, org_name: str) -> List[Dict]:
        """
        获取指定组织的所有公开仓库

        Args:
            org_name: GitHub组织名

        Returns:
            仓库信息列表
        """
        try:
            org = self.github.get_organization(org_name)
            repos = []

            for repo in org.get_repos():
                if not repo.private:
                    repos.append({
                        'name': repo.name,
                        'full_name': repo.full_name,
                        'url': repo.html_url,
                        'clone_url': repo.clone_url,
                        'description': repo.description,
                        'updated_at': repo.updated_at,
                        'pushed_at': repo.pushed_at,
                        'created_at': repo.created_at,
                        'stargazers_count': repo.stargazers_count,
                        'language': repo.language,
                    })

            return repos
        except GithubException as e:
            print(f"❌ 获取组织仓库失败: {e}")
            return []

    def search_ai_repos(self, max_repos: int = MAX_REPOS_PER_SEARCH,
                        skip_filter: Optional[Callable] = None,
                        prefer_new: bool = True,
                        sort_by: str = "updated") -> List[Dict]:
        """
        搜索AI相关的GitHub项目

        Args:
            max_repos: 最大返回仓库数量
            skip_filter: 可选的过滤函数，接受仓库全名，返回True表示跳过该仓库
            prefer_new: 是否优先返回未扫描过的新仓库
            sort_by: GitHub搜索排序方式 ('updated'=最近更新, 'stars'=星标数, 'best_match'=最佳匹配)

        Returns:
            仓库信息列表
        """
        all_repos = []
        seen_repos = set()
        skipped_count = 0
        new_repos_count = 0

        for keyword in AI_SEARCH_KEYWORDS:
            try:
                print(f"🔍 搜索关键词: {keyword}")
                self.wait_for_rate_limit()

                # 搜索代码，支持排序
                query = f'{keyword} in:file language:python'
                results = self.github.search_code(query, order='desc', sort=sort_by)

                # 从代码搜索结果中提取仓库
                for code in results:
                    # 如果已经找到足够的仓库，停止搜索
                    if len(all_repos) >= max_repos:
                        break

                    repo = code.repository

                    # 跳过私有仓库和已经见过的仓库
                    if repo.private or repo.full_name in seen_repos:
                        continue

                    seen_repos.add(repo.full_name)

                    # 如果提供了过滤函数，检查是否应该跳过
                    if skip_filter and skip_filter(repo.full_name):
                        skipped_count += 1
                        # 如果 prefer_new 为 True，跳过已扫描的继续找新的
                        if prefer_new:
                            continue
                        else:
                            print(f"  ⏭️  跳过已扫描: {repo.full_name}")
                            continue

                    # 添加到结果列表
                    all_repos.append({
                        'name': repo.name,
                        'full_name': repo.full_name,
                        'url': repo.html_url,
                        'clone_url': repo.clone_url,
                        'description': repo.description,
                        'updated_at': repo.updated_at,
                        'pushed_at': repo.pushed_at,
                        'created_at': repo.created_at,
                        'stargazers_count': repo.stargazers_count,
                        'language': repo.language,
                    })

                    if skip_filter and not skip_filter(repo.full_name):
                        new_repos_count += 1

                # 延迟以避免触发速率限制
                time.sleep(SEARCH_DELAY_SECONDS)

                if len(all_repos) >= max_repos:
                    print(f"✅ 已找到 {len(all_repos)} 个仓库（其中 {new_repos_count} 个新仓库，跳过了 {skipped_count} 个已扫描的）")
                    break

            except GithubException as e:
                print(f"⚠️  搜索 '{keyword}' 时出错: {e}")
                continue

        if skipped_count > 0 and len(all_repos) < max_repos:
            print(f"ℹ️  找到 {len(all_repos)} 个仓库（其中 {new_repos_count} 个新仓库，跳过了 {skipped_count} 个已扫描的）")

        # 如果 prefer_new，按更新时间降序排列（最新的优先）
        if prefer_new:
            all_repos.sort(
                key=lambda r: r.get('updated_at') or datetime.min,
                reverse=True
            )

        return all_repos

    def search_repos_by_query(self, query: str, max_repos: int = 50,
                              sort_by: str = "updated",
                              skip_filter: Optional[Callable] = None,
                              prefer_new: bool = True) -> List[Dict]:
        """
        使用自定义查询搜索仓库

        Args:
            query: GitHub搜索查询语句
            max_repos: 最大返回数量
            sort_by: 排序方式 ('updated', 'stars', 'forks', 'help-wanted-issues')
            skip_filter: 过滤函数
            prefer_new: 是否优先新仓库

        Returns:
            仓库信息列表
        """
        all_repos = []
        seen_repos = set()
        skipped_count = 0

        try:
            print(f"🔍 自定义搜索: {query}")
            self.wait_for_rate_limit()

            results = self.github.search_repositories(query, sort=sort_by, order='desc')

            for repo in results:
                if len(all_repos) >= max_repos:
                    break

                if repo.private or repo.full_name in seen_repos:
                    continue

                seen_repos.add(repo.full_name)

                if skip_filter and skip_filter(repo.full_name):
                    skipped_count += 1
                    if prefer_new:
                        continue

                all_repos.append({
                    'name': repo.name,
                    'full_name': repo.full_name,
                    'url': repo.html_url,
                    'clone_url': repo.clone_url,
                    'description': repo.description,
                    'updated_at': repo.updated_at,
                    'pushed_at': repo.pushed_at,
                    'created_at': repo.created_at,
                    'stargazers_count': repo.stargazers_count,
                    'language': repo.language,
                })

            time.sleep(SEARCH_DELAY_SECONDS)

        except GithubException as e:
            print(f"⚠️  搜索时出错: {e}")

        if prefer_new:
            all_repos.sort(
                key=lambda r: r.get('updated_at') or datetime.min,
                reverse=True
            )

        return all_repos

    def get_repo_files(self, repo_full_name: str, path: str = "") -> List[Dict]:
        """
        获取仓库中的文件列表

        Args:
            repo_full_name: 仓库全名 (owner/repo)
            path: 文件路径

        Returns:
            文件信息列表
        """
        try:
            repo = self.github.get_repo(repo_full_name)
            contents = repo.get_contents(path)

            files = []
            for content in contents:
                if content.type == "dir":
                    # 递归获取子目录文件
                    files.extend(self.get_repo_files(repo_full_name, content.path))
                else:
                    files.append({
                        'path': content.path,
                        'name': content.name,
                        'download_url': content.download_url,
                        'sha': content.sha,
                    })

            return files
        except GithubException as e:
            # 403 错误直接跳过，不等待
            if e.status == 403:
                print(f"  ⏭️  跳过: 无权访问 (403 Forbidden)")
            else:
                print(f"⚠️  获取文件列表失败: {e}")
            return []

    def get_file_content(self, repo_full_name: str, file_path: str) -> Optional[str]:
        """
        获取文件内容

        Args:
            repo_full_name: 仓库全名 (owner/repo)
            file_path: 文件路径

        Returns:
            文件内容（文本）
        """
        try:
            repo = self.github.get_repo(repo_full_name)
            content = repo.get_contents(file_path)

            # 解码内容
            try:
                return content.decoded_content.decode('utf-8')
            except UnicodeDecodeError:
                # 如果是二进制文件，返回None
                return None
        except GithubException as e:
            # 403 错误直接跳过，不打印错误
            if e.status == 403:
                pass  # 静默跳过
            return None

    def get_repo_info(self, repo_full_name: str) -> Optional[Dict]:
        """
        获取仓库详细信息

        Args:
            repo_full_name: 仓库全名 (owner/repo)

        Returns:
            仓库信息字典
        """
        try:
            repo = self.github.get_repo(repo_full_name)
            return {
                'name': repo.name,
                'full_name': repo.full_name,
                'url': repo.html_url,
                'clone_url': repo.clone_url,
                'description': repo.description,
                'updated_at': repo.updated_at,
                'pushed_at': repo.pushed_at,
                'created_at': repo.created_at,
                'stargazers_count': repo.stargazers_count,
                'forks_count': repo.forks_count,
                'language': repo.language,
                'topics': repo.get_topics(),
                'license': repo.license.spdx_id if repo.license else None,
                'size': repo.size,
            }
        except GithubException as e:
            print(f"⚠️  获取仓库信息失败: {e}")
            return None
