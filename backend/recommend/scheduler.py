"""
scheduler.py - 定时更新推荐系统
"""

import subprocess
import schedule
import time
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_recommend():
    """运行推荐训练"""
    print("=" * 50)
    print(f"🔄 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始推荐训练...")
    print("=" * 50)

    try:
        # 运行纯 Python 推荐
        result = subprocess.run(
            [sys.executable, '-m', 'recommend.pure_recommend'],
            capture_output=False,
            text=True,
            timeout=300  # 5分钟超时
        )
        print(f"✅ 推荐训练完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True

    except subprocess.TimeoutExpired:
        print(f"❌ 推荐训练超时 (5分钟)")
        return False
    except Exception as e:
        print(f"❌ 推荐训练失败: {e}")
        return False


def run_manual():
    """手动触发一次训练"""
    print("\n🚀 手动触发推荐训练...")
    run_recommend()
    print("✅ 完成\n")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='只运行一次')
    args = parser.parse_args()

    if args.once:
        run_manual()
    else:
        # 首次运行
        print("🚀 首次运行推荐训练...")
        run_recommend()

        # 定时任务：每天凌晨 2:00、下午 14:00 各运行一次
        schedule.every().day.at("02:00").do(run_recommend)
        schedule.every().day.at("14:00").do(run_recommend)

        print("\n⏰ 定时任务已设置:")
        print("   - 每天 02:00 更新推荐")
        print("   - 每天 14:00 更新推荐")
        print("   - 按 Ctrl+C 停止\n")

        while True:
            schedule.run_pending()
            time.sleep(60)