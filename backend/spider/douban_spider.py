"""
douban_spider.py - 豆瓣电影爬虫（手机版专用）
针对 m.douban.com 的 HTML 结构优化
"""

import requests
import time
import mysql.connector
import random
import re
from bs4 import BeautifulSoup

# ====== 数据库配置 ======
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 改成你的密码
    'database': 'movie_app',
    'charset': 'utf8mb4'
}

# ====== 请求头（模拟手机浏览器） ======
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Referer': 'https://m.douban.com/',
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def movie_exists(douban_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM movies WHERE douban_id = %s', (str(douban_id),))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def insert_movie(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM movies WHERE douban_id = %s', (str(data['douban_id']),))
    sql = """
        INSERT INTO movies 
        (title, year, genre, rating, description, poster, video_url, douban_id, douban_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (
        data['title'],
        data['year'],
        data['genre'],
        data['rating'],
        data['description'],
        data['poster'],
        data['video_url'],
        str(data['douban_id']),
        data['douban_url']
    ))
    conn.commit()
    movie_id = cursor.lastrowid
    conn.close()
    return movie_id


def fetch_html(url, max_retries=3):
    """获取 HTML"""
    for i in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 403:
                print(f'  ⚠️ 被反爬，等待后重试 {i+1}/{max_retries}...')
                time.sleep(random.uniform(3, 6))
            else:
                print(f'  ⚠️ 状态码 {resp.status_code}，重试 {i+1}/{max_retries}...')
                time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f'  ⚠️ 请求失败: {e}，重试 {i+1}/{max_retries}...')
            time.sleep(random.uniform(2, 4))
    return None


def parse_movie_detail_from_mobile(html, douban_id):
    """
    从手机版详情页解析电影信息
    基于你提供的 HTML 结构：
    - title: <title> 肖申克的救赎 - 电影 - 豆瓣 </title>
    - rating: <meta itemprop="ratingValue" content="9.7">
    - description: <meta name="description" content="...">
    - poster: <meta property="og:image" content="...">
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # ----- 标题：从 <title> 提取 -----
        title_tag = soup.select_one('title')
        title = '未知'
        if title_tag:
            title_text = title_tag.text.strip()
            # 格式: "肖申克的救赎 - 电影 - 豆瓣"
            if ' - 电影 - 豆瓣' in title_text:
                title = title_text.replace(' - 电影 - 豆瓣', '').strip()
            elif ' - 豆瓣' in title_text:
                title = title_text.replace(' - 豆瓣', '').strip()
            else:
                title = title_text
        
        # ----- 评分：从 meta 标签提取 -----
        rating = 0.0
        rating_meta = soup.select_one('meta[itemprop="ratingValue"]')
        if rating_meta:
            try:
                rating = float(rating_meta.get('content', '0'))
            except:
                rating = 0.0
        
        # ----- 简介：从 meta description 提取 -----
        description = ''
        desc_meta = soup.select_one('meta[name="description"]')
        if desc_meta:
            description = desc_meta.get('content', '')
            # 去掉开头的 "肖申克的救赎豆瓣评分：9.7 简介："
            if '简介：' in description:
                description = description.split('简介：')[-1].strip()
            elif '豆瓣评分：' in description:
                # 尝试提取评分后的内容
                parts = description.split('豆瓣评分：')
                if len(parts) > 1:
                    # 去掉评分数字部分
                    desc_part = parts[1]
                    if ' ' in desc_part:
                        desc_part = desc_part.split(' ', 1)[-1]
                    if '简介：' in desc_part:
                        description = desc_part.split('简介：')[-1].strip()
                    else:
                        description = desc_part.strip()
        
        # ----- 海报：从 og:image 提取 -----
        poster = ''
        poster_meta = soup.select_one('meta[property="og:image"]')
        if poster_meta:
            poster = poster_meta.get('content', '')
            # 手机版图片可能带参数，去掉参数获取大图
            if '?imageView2' in poster:
                poster = poster.split('?')[0]
        
        # ----- 类型和年份：从页面正文提取 -----
        # 手机版通常有 <span>类型: xxx</span> 或类似结构
        genre = ''
        year = ''
        
        # 尝试从页面中提取类型
        genre_patterns = [
            r'类型[：:]\s*([^<>\n]+)',
            r'<span>类型[：:]\s*([^<]+)</span>',
        ]
        for pattern in genre_patterns:
            match = re.search(pattern, html)
            if match:
                genre = match.group(1).strip()
                # 清理多余的标签
                genre = re.sub(r'<[^>]+>', '', genre)
                break
        
        # 尝试提取年份
        year_patterns = [
            r'(\d{4})[年\-]\s*(?:上映|\(|（)',
            r'上映[：:]\s*(\d{4})',
            r'<span>(\d{4})</span>',
        ]
        for pattern in year_patterns:
            match = re.search(pattern, html)
            if match:
                year = match.group(1)
                break
        
        # 如果没提取到年份，尝试从标题或URL提取
        if not year:
            year_match = re.search(r'(\d{4})', title)
            if year_match:
                year = year_match.group(1)
        
        return {
            'title': title,
            'year': year,
            'genre': genre,
            'rating': rating,
            'description': description[:500],
            'poster': poster
        }
        
    except Exception as e:
        print(f'    ⚠️ 解析详情页失败: {e}')
        return None


def crawl_douban_top250():
    """抓取豆瓣 Top250（手机版）"""
    print('📥 开始抓取豆瓣 Top250（手机版）...')
    
    movies = []
    # 手机版 Top250 列表页
    base_url = 'https://m.douban.com/top250'
    
    for start in range(0, 250, 25):
        url = f'{base_url}?start={start}'
        print(f'  📄 抓取第 {start//25 + 1} 页: {url}')
        
        html = fetch_html(url)
        if not html:
            print(f'  ❌ 第 {start//25 + 1} 页抓取失败')
            continue
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 手机版 Top250 的条目选择器
        # 常见结构: <div class="item"> 或 <li class="subject-item">
        items = soup.select('.item') or soup.select('.subject-item') or soup.select('li[data-id]')
        
        if not items:
            # 尝试另一种选择器
            items = soup.select('a[href*="/movie/subject/"]')
            # 过滤掉非电影链接
            items = [a for a in items if '/movie/subject/' in a.get('href', '') and a.find('img')]
        
        if not items:
            print(f'  ⚠️ 第 {start//25 + 1} 页没有数据')
            continue
        
        for item in items:
            # 提取豆瓣ID
            douban_id = None
            
            # 从 data-id 属性获取
            if item.get('data-id'):
                douban_id = item.get('data-id')
            
            # 从链接获取
            if not douban_id:
                link = item.find('a', href=re.compile(r'/movie/subject/\d+/'))
                if not link:
                    link = item.select_one('a[href*="/movie/subject/"]')
                if link:
                    href = link.get('href', '')
                    id_match = re.search(r'/movie/subject/(\d+)/', href)
                    if id_match:
                        douban_id = id_match.group(1)
            
            if not douban_id:
                continue
            
            # 提取标题
            title = ''
            title_elem = item.select_one('.title') or item.select_one('h3') or item.select_one('.name')
            if title_elem:
                title = title_elem.text.strip()
            else:
                # 从链接文本获取
                link = item.find('a', href=re.compile(r'/movie/subject/\d+/'))
                if link:
                    title = link.text.strip()
            
            # 提取评分
            rating = 0.0
            rating_elem = item.select_one('.rating') or item.select_one('.score') or item.select_one('.rating-num')
            if rating_elem:
                rating_text = rating_elem.text.strip()
                try:
                    rating = float(rating_text)
                except:
                    # 尝试从文本中提取数字
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating = float(rating_match.group(1))
            
            # 提取年份
            year = ''
            year_elem = item.select_one('.year') or item.select_one('.date')
            if year_elem:
                year_text = year_elem.text.strip()
                year_match = re.search(r'(\d{4})', year_text)
                if year_match:
                    year = year_match.group(1)
            
            # 提取海报
            poster = ''
            img = item.find('img')
            if img:
                poster = img.get('src') or img.get('data-src') or ''
            
            # 获取详情页URL
            detail_url = f'https://m.douban.com/movie/subject/{douban_id}/'
            
            # 检查是否已存在
            if movie_exists(douban_id):
                print(f'    ⏭️ {title} 已存在，跳过')
                continue
            
            # 获取详情页（获取类型和完整简介）
            print(f'    🔍 获取详情: {title}...')
            detail_html = fetch_html(detail_url)
            
            genre = ''
            description = ''
            if detail_html:
                detail = parse_movie_detail_from_mobile(detail_html, douban_id)
                if detail:
                    genre = detail.get('genre', '')
                    description = detail.get('description', '')[:500]
                    if not poster:
                        poster = detail.get('poster', '')
                    if not year:
                        year = detail.get('year', '')
                    if not rating:
                        rating = detail.get('rating', 0.0)
                    if not title:
                        title = detail.get('title', title)
            
            movie_data = {
                'title': title,
                'year': year,
                'genre': genre,
                'rating': rating,
                'description': description,
                'poster': poster,
                'video_url': 'https://www.w3schools.com/html/mov_bbb.mp4',
                'douban_id': douban_id,
                'douban_url': detail_url
            }
            
            movies.append(movie_data)
            print(f'    ✅ {title} ({year}) ⭐{rating}')
            
            # 延时控制
            time.sleep(random.uniform(0.8, 1.5))
        
        # 页与页之间延时
        time.sleep(random.uniform(2, 4))
    
    return movies


def save_to_db(movies):
    """保存到数据库"""
    print('💾 保存到数据库...')
    
    new_count = 0
    for movie in movies:
        if not movie or not movie.get('title'):
            continue
        insert_movie(movie)
        new_count += 1
        print(f'  ✅ 插入: {movie["title"]}')
    
    print(f'📊 新增 {new_count} 部')


def main():
    print('=' * 50)
    print('🎬 豆瓣电影爬虫启动（手机版）')
    print('=' * 50)
    
    movies = crawl_douban_top250()
    print(f'\n📊 Top250 抓取完成: {len(movies)} 部\n')
    
    save_to_db(movies)
    
    print('=' * 50)
    print('✅ 爬虫运行完成！')
    print('=' * 50)


if __name__ == '__main__':
    main()