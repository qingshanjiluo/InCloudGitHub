#!/usr/bin/env python3
"""
InCloud GitHub 云上扫描器 - 主程序
用于扫描GitHub仓库中泄露的AI API密钥和敏感信息

支持功能：
  - 自动识别 SK 密钥类型并推断 Base URL 和可用模型
  - 优先扫描新仓库（不重复扫描）
  - 按更新时间排序，最新仓库优先
  - 扫描历史管理和统计
"""
import argparse
import sys
import os
from datetime import datetime
from config import GITHUB_TOKEN, PREFER_NEW_REPOS, DEFAULT_SORT_BY, SKIP_SCANNED, SCAN_TIMEOUT_MINUTES
from scanner import CloudScanner
from scan_history import ScanHistory
from sk_analyzer import SKAnalyzer


def print_banner():
    """打印程序横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        InCloud GitHub 云上扫描器 v2.0                      ║
║        AI API Key Leakage Scanner                         ║
║                                                           ║
║        功能:                                               ║
║        • 自动识别 SK 密钥类型 & 推断 Base URL/模型         ║
║        • 优先扫描新仓库，不重复扫描                        ║
║        • 按更新时间排序，最新仓库优先                      ║
║        • 扫描历史管理和统计                                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


def validate_github_token() -> bool:
    """验证GitHub Token是否存在"""
    if not GITHUB_TOKEN:
        print("❌ 错误: 未找到 GitHub Token")
        print("\n请按以下步骤设置：")
        print("1. 复制 .env.example 为 .env")
        print("2. 在 https://github.com/settings/tokens 创建 Personal Access Token")
        print("3. 将 Token 添加到 .env 文件中的 GITHUB_TOKEN 变量")
        return False
    return True


def cmd_history(args):
    """处理 --history 命令"""
    history = ScanHistory()
    history.print_statistics()

    if args.history_detail:
        repos_with_findings = history.get_repos_with_findings()
        if repos_with_findings:
            print(f"\n📋 发现问题的仓库（共 {len(repos_with_findings)} 个）:")
            for repo_name, count in repos_with_findings:
                print(f"  • {repo_name}: {count} 个发现")

        if args.history_clear:
            confirm = input("\n⚠️  确定要清空扫描历史吗？(y/N): ")
            if confirm.lower() == 'y':
                history.clear_history()


def cmd_list_providers(args):
    """处理 --list-providers 命令"""
    print("\n🌐 已知 AI 服务商列表:")
    print("━" * 80)
    providers = SKAnalyzer.get_all_providers()

    # 按类型分组
    by_type = {}
    for p in providers:
        t = p["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(p)

    type_names = {
        "official": "🏢 官方服务",
        "proxy": "🔄 中转/代理服务",
        "domestic": "🇨🇳 国内大模型",
        "cloud": "☁️ 云服务商",
        "local": "💻 本地部署",
    }

    for t, ps in by_type.items():
        print(f"\n{type_names.get(t, t)}:")
        for p in ps:
            base_url = p["base_url"] or "自动检测"
            models = ", ".join(p["models"][:5])
            if len(p["models"]) > 5:
                models += "..."
            print(f"  • {p['name']}")
            print(f"    🌐 {base_url}")
            print(f"    🤖 {models}")


def main():
    """主函数"""
    print_banner()

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description='扫描 GitHub 仓库中泄露的 AI API 密钥和敏感信息',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 扫描指定用户的所有公开仓库
  python scan_github.py --user username

  # 扫描指定组织的所有公开仓库
  python scan_github.py --org organization_name

  # 扫描单个仓库
  python scan_github.py --repo owner/repo_name

  # 自动搜索并扫描 AI 相关项目（新仓库优先）
  python scan_github.py --auto

  # 自动搜索并按星标排序
  python scan_github.py --auto --sort-by stars

  # 自动搜索并扫描指定数量的仓库
  python scan_github.py --auto --max-repos 100

  # 查看扫描历史统计
  python scan_github.py --history

  # 列出所有已知的 AI 服务商
  python scan_github.py --list-providers
        """
    )

    # 添加参数
    parser.add_argument(
        '--user',
        type=str,
        help='扫描指定 GitHub 用户的所有公开仓库'
    )

    parser.add_argument(
        '--org',
        type=str,
        help='扫描指定 GitHub 组织的所有公开仓库'
    )

    parser.add_argument(
        '--repo',
        type=str,
        help='扫描单个仓库 (格式: owner/repo_name)'
    )

    parser.add_argument(
        '--auto',
        action='store_true',
        help='自动搜索并扫描 AI 相关项目'
    )

    parser.add_argument(
        '--max-repos',
        type=int,
        default=50,
        help='自动模式下最大扫描仓库数 (默认: 50)'
    )

    parser.add_argument(
        '--token',
        type=str,
        help='GitHub Personal Access Token (可选，默认从 .env 读取)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        help='报告输出目录 (可选，默认: ./scan_reports)'
    )

    parser.add_argument(
        '--no-skip-scanned',
        action='store_true',
        help='不跳过已扫描的仓库，强制重新扫描所有仓库'
    )

    # ===== 新增参数 =====
    parser.add_argument(
        '--sort-by',
        type=str,
        choices=['updated', 'stars', 'best_match'],
        default=DEFAULT_SORT_BY,
        help='排序方式: updated=最近更新, stars=星标数, best_match=最佳匹配 (默认: updated)'
    )

    parser.add_argument(
        '--no-prefer-new',
        action='store_true',
        help='不优先扫描新仓库，按默认顺序扫描'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=SCAN_TIMEOUT_MINUTES,
        help='扫描超时时间（分钟）(默认: 50)'
    )

    parser.add_argument(
        '--history',
        action='store_true',
        help='查看扫描历史统计'
    )

    parser.add_argument(
        '--history-detail',
        action='store_true',
        help='查看扫描历史详细信息（与 --history 一起使用）'
    )

    parser.add_argument(
        '--history-clear',
        action='store_true',
        help='清空扫描历史（与 --history 一起使用，需要确认）'
    )

    parser.add_argument(
        '--list-providers',
        action='store_true',
        help='列出所有已知的 AI 服务商信息'
    )

    # 解析参数
    args = parser.parse_args()

    # 处理 --list-providers
    if args.list_providers:
        cmd_list_providers(args)
        return

    # 处理 --history
    if args.history:
        cmd_history(args)
        return

    # 检查是否提供了至少一个扫描选项
    if not any([args.user, args.org, args.repo, args.auto]):
        parser.print_help()
        print("\n❌ 错误: 请至少指定一个扫描选项 (--user, --org, --repo, 或 --auto)")
        print("\n💡 提示: 使用 --list-providers 查看已知 AI 服务商")
        print("💡 提示: 使用 --history 查看扫描历史")
        sys.exit(1)

    # 验证 GitHub Token
    token = args.token or GITHUB_TOKEN
    if not token:
        if not validate_github_token():
            sys.exit(1)

    # 设置输出目录
    if args.output_dir:
        os.environ['OUTPUT_DIR'] = args.output_dir

    try:
        # 创建扫描器实例
        skip_scanned = not args.no_skip_scanned
        prefer_new = not args.no_prefer_new

        scanner = CloudScanner(
            token,
            skip_scanned=skip_scanned,
            timeout_minutes=args.timeout,
            prefer_new=prefer_new
        )

        # 打印扫描策略
        print(f"\n📋 扫描策略:")
        print(f"  • 跳过已扫描: {'✅ 是' if skip_scanned else '❌ 否'}")
        print(f"  • 优先新仓库: {'✅ 是' if prefer_new else '❌ 否'}")
        print(f"  • 排序方式: {args.sort_by}")
        print(f"  • 超时时间: {args.timeout} 分钟")
        print()

        # 根据参数执行不同的扫描
        if args.user:
            report_path = scanner.scan_user(args.user, sort_by=args.sort_by)
        elif args.org:
            report_path = scanner.scan_organization(args.org, sort_by=args.sort_by)
        elif args.repo:
            report_path = scanner.scan_single_repo(args.repo)
        elif args.auto:
            report_path = scanner.scan_ai_projects(
                max_repos=args.max_repos,
                sort_by=args.sort_by
            )

        print(f"\n✅ 扫描完成！")
        print(f"📄 报告已保存至: {report_path}")

        # 打印扫描历史摘要
        print(f"\n{scanner.get_scan_history_summary()}")

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断扫描")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 扫描过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
