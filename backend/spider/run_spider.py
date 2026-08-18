"""
run_spider.py - 爬虫运行入口（支持定时任务）
"""
import subprocess
import schedule
import time
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_spider():
    """运行爬虫"""
    print('\n' + '=' * 50)
    print(f'🔄 定时爬虫开始: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 50)

    try:
        # 运行爬虫
        subprocess.run(
            ['python', '-m', 'spider.douban_spider'],
            check=True,
            capture_output=False
        )
        print(f'✅ 爬虫完成: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    except Exception as e:
        print(f'❌ 爬虫失败: {e}')


# 测试运行
if __name__ == '__main__':
    # 先手动运行一次
    print(' 首次运行爬虫...')
    run_spider()

    # 设置定时任务（每天凌晨 3:00）
    print('\n⏰ 定时任务已设置: 每天 03:00')
    schedule.every().day.at("03:00").do(run_spider)

    while True:
        schedule.run_pending()
        time.sleep(60)