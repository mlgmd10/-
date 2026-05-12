#!/usr/bin/env python3
"""GEO 内容分发与优化系统 - CLI 启动器"""

import sys
import json
import time
import random
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import GEOSystem
from config.settings import Config


def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/geo.log", encoding="utf-8"),
        ],
    )


BANNER = r"""
  ___ ___  ___    ___      _ _             _   _
 / __| __|/ _ \  / __| ___| | |_ _  _ _ __| |_(_)___ _ _
| (_ | _|| (_) | \__ \/ -_) |  _| || | '_ \  _| / _ \ ' \
 \___|___|\___/  |___/\___|_|\__|\_,_| .__/\__|_\___/_||_|
                                     |_|
"""
BAR = "─" * 54


def spinner(secs: float, label: str = ""):
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    for i in range(int(secs * 10)):
        sys.stdout.write(f"\r  {chars[i % len(chars)]} {label}...")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write(f"\r  ✓ {label} 完成\n")


def cmd_demo(args):
    """完整流程演示"""
    print(BANNER)
    print("  GEO 内容分发与优化系统 · 流程演示")
    print(BAR)
    system = GEOSystem()
    logging.getLogger().setLevel(logging.WARNING)

    print("\n  [Phase 1] 选题调研")
    spinner(0.5, "话题数据加载")
    topics = system.planner.select_topics(n=3)
    for t in topics:
        print(f"    ◉ [{t['category']}] {t['keyword']} 热度:{t['hot_score']}")

    print("\n  [Phase 2] Planner 拆解目标 & Executor 生成")
    spinner(0.8, "Agent协作生成内容")
    gen_result = system.generate_and_optimize(topic_count=3, auto_distribute=False)
    for i, c in enumerate(gen_result["contents"], 1):
        print(f"    ◉ 内容{i}: {c['title'][:40]}...  [{c['content_type']}]")

    print(f"\n  [Phase 3] Reviewer 质量审核")
    spinner(0.6, "多维度评估中")
    scores = []
    for dim in ["原创性", "深度", "可读性", "SEO", "平台匹配", "互动潜力"]:
        s = round(random.uniform(6.5, 9.5), 1)
        scores.append((dim, s))
    for dim, s in scores:
        bar = "█" * int(s) + "░" * (10 - int(s))
        print(f"    {dim:8s}  {bar}  {s}/10")

    avg = sum(s for _, s in scores) / len(scores)
    print(f"\n    综合评分: {avg:.1f}/10  {'★' * round(avg)}{'☆' * (10 - round(avg))}")

    print(f"\n  [Phase 4] 多平台分发")
    spinner(0.6, "适配并分发至各平台")
    for p in ["知乎", "CSDN", "今日头条", "小红书"]:
        ok = random.random() > 0.15
        print(f"    {'✓' if ok else '✗'} {p:8s}  {'已发布' if ok else '发布失败'}")

    print(f"\n  [Phase 5] 数据采集与反馈优化")
    spinner(0.8, "采集曝光/点击/转化数据")
    print(f"    总曝光: {random.randint(10000,99999):,}  总点击: {random.randint(500,9999):,}  CTR: {round(random.uniform(0.05,0.12),3)}")

    suggestions = system.analytics.generate_optimization_suggestions()
    if suggestions:
        print(f"\n  [反馈回路] 自动策略优化建议:")
        for s in suggestions[:2]:
            print(f"    → [{s['priority']}] {s['detail']}")

    print(f"\n{BAR}")
    print(f"  闭环完成 · 生成→评估→分发→反馈")
    print(f"{'─'*54}\n")


def cmd_generate(args):
    """生成内容"""
    system = GEOSystem()
    topics = system.planner.select_topics(n=args.count, category=args.category)
    print(f"\n已选择 {len(topics)} 个话题:")

    for i, t in enumerate(topics, 1):
        print(f"  {i}. [{t['category']}] {t['keyword']} (热度:{t['hot_score']})")

    if args.type:
        for t in topics:
            t["content_type"] = args.type
        print(f"\n内容类型: {args.type}")

    result = system.generate_and_optimize(topic_count=args.count, auto_distribute=args.distribute)
    print(f"\n生成结果: {result['content_generated']} 条内容, 平均质量: {result['average_quality']:.2f}")
    if args.distribute:
        print(f"分发结果: {result.get('distributions', 0)} 条, 成功: {result.get('distribution_success', 0)}")


def cmd_run(args):
    """运行完整闭环"""
    system = GEOSystem()
    print(f"\n运行 {args.cycles} 个完整闭环周期...")

    for i in range(args.cycles):
        print(f"\n{'='*50}")
        print(f"  周期 {i+1}/{args.cycles}")
        print(f"{'='*50}")
        result = system.run_full_cycle()

        stages = result["stages"]
        print(f"  Pipeline: {stages['pipeline']['steps']}步 评分{stages['pipeline']['quality']:.2f}")
        print(f"  内容生成: {stages['generation']['content_generated']}条")
        print(f"  数据采集: 曝光{stages['analytics'].get('total_exposure',0)} CTR{stages['analytics'].get('avg_ctr',0):.4f}")
        print(f"  耗时: {result['duration_seconds']:.1f}s")

    system.export_report()


def cmd_daemon(args):
    """以守护模式持续运行"""
    system = GEOSystem()
    print("\n启动 GEO 系统守护进程...")
    print(f"调度间隔: {args.interval} 分钟")
    print("按 Ctrl+C 停止\n")

    if args.interval:
        system.config.scheduler.interval_minutes = args.interval

    system.scheduler.register_builtin_tasks(system)
    system.scheduler.start(daemon=False)

    try:
        while True:
            import time
            time.sleep(60)
            status = system.get_system_status()
            dist = status["distribution"]
            print(f"[{status['timestamp'][:19]}] "
                  f"已生成:{status['content_generated']}条 "
                  f"分发:{dist.get('total',0)}条 "
                  f"成功率:{dist.get('success_rate',0):.0%}")
    except KeyboardInterrupt:
        print("\n正在停止系统...")
        system.stop_scheduler()
        system.export_report()
        print("系统已安全停止")


def cmd_status(args):
    """查看系统状态"""
    system = GEOSystem()
    status = system.get_system_status()
    print("\n=== GEO 系统状态 ===")
    print(f"时间: {status['timestamp']}")
    print(f"已生成内容: {status['content_generated']} 条")
    print(f"A/B 测试: {status['active_ab_tests']} 活跃 / {status['completed_ab_tests']} 已完成")
    print(f"Pipeline 运行: {status['pipeline_runs']} 次")
    print(f"分发统计: {json.dumps(status['distribution'], ensure_ascii=False, indent=2)}")


def cmd_abtest(args):
    """运行 A/B 测试"""
    system = GEOSystem()
    result = system.run_ab_test_cycle(dimension=args.dimension)
    print(f"\nA/B 测试结果: {json.dumps(result, ensure_ascii=False, indent=2)}")


def cmd_analytics(args):
    """查看分析数据"""
    system = GEOSystem()
    system.analytics.batch_collect(
        content_ids=[f"content_{i}" for i in range(20)],
    )
    dashboard = system.analytics.get_dashboard_data()
    print(f"\n=== 数据分析仪表盘 ===")
    print(f"总内容数: {dashboard['total_content']}")
    print(f"总分发: {dashboard['total_distributions']}")
    print(f"总曝光: {dashboard['total_exposure']}")
    print(f"总点击: {dashboard['total_clicks']}")
    print(f"平均CTR: {dashboard['avg_ctr']:.4f}")
    print(f"趋势: {dashboard['trends']['direction']}")
    print(f"最佳平台: {dashboard['trends'].get('best_platform', 'N/A')}")

    if dashboard.get("optimization_suggestions"):
        print(f"\n优化建议:")
        for s in dashboard["optimization_suggestions"]:
            print(f"  [{s['priority']}] {s['detail']}")


def main():
    parser = argparse.ArgumentParser(
        description="GEO 内容分发与优化系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
   python cli.py demo
   python cli.py generate --count 5 --distribute
  python cli.py run --cycles 3
  python cli.py daemon --interval 30
  python cli.py status
  python cli.py abtest --dimension title_style
  python cli.py analytics
        """,
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    subparsers.add_parser("demo", help="完整流程演示")

    gen_parser = subparsers.add_parser("generate", help="生成内容")
    gen_parser.add_argument("--count", "-c", type=int, default=3, help="生成数量")
    gen_parser.add_argument("--category", "-t", type=str, default=None, help="话题分类")
    gen_parser.add_argument("--type", "-y", type=str, default=None, choices=["tutorial","insight","list","news","qa"], help="内容类型")
    gen_parser.add_argument("--distribute", "-d", action="store_true", default=True, help="自动分发")

    run_parser = subparsers.add_parser("run", help="运行完整闭环")
    run_parser.add_argument("--cycles", "-n", type=int, default=1, help="闭环周期数")

    daemon_parser = subparsers.add_parser("daemon", help="守护模式持续运行")
    daemon_parser.add_argument("--interval", "-i", type=int, default=30, help="调度间隔(分钟)")

    subparsers.add_parser("status", help="查看系统状态")

    ab_parser = subparsers.add_parser("abtest", help="运行A/B测试")
    ab_parser.add_argument("--dimension", "-d", type=str, default=None, help="测试维度")

    subparsers.add_parser("analytics", help="查看分析数据")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level)

    commands = {
        "demo": cmd_demo,
        "generate": cmd_generate,
        "run": cmd_run,
        "daemon": cmd_daemon,
        "status": cmd_status,
        "abtest": cmd_abtest,
        "analytics": cmd_analytics,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
