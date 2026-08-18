"""
tmdb_spider.py - 使用 TMDB API 获取电影数据
"""
import requests
import time
import mysql.connector
import random

# ====== 配置 ======
TMDB_API_KEY = '0c5f86f81aca605f029a77dc4b242463'  # 去 https://www.themoviedb.org/settings/api 申请
TMDB_BASE_URL = 'https://api.themoviedb.org/3'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 改成你的密码
    'database': 'movie_app',
    'charset': 'utf8mb4'
}

# ====== 数据库操作 ======
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def movie_exists(tmdb_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM movies WHERE douban_id = %s', (str(tmdb_id),))
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
    conn.close()


def fetch_tmdb(endpoint, params=None):
    """调用 TMDB API"""
    url = f"{TMDB_BASE_URL}/{endpoint}"
    all_params = {
        'api_key': TMDB_API_KEY,
        'language': 'zh-CN',
        'region': 'CN'
    }
    if params:
        all_params.update(params)
    
    try:
        resp = requests.get(url, params=all_params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f'  ⚠️ API 返回 {resp.status_code}')
            return None
    except Exception as e:
        print(f'  ⚠️ 请求失败: {e}')
        return None


def crawl_tmdb_top_rated():
    """抓取 TMDB 评分最高电影"""
    print(' 从 TMDB 获取评分最高电影...')
    
    movies = []
    for page in range(1, 11):  # 抓取 10 页，共 200 部
        print(f'   抓取第 {page} 页')
        
        data = fetch_tmdb('movie/top_rated', {'page': page})
        if not data or 'results' not in data:
            print(f'  ❌ 第 {page} 页抓取失败')
            continue
        
        for item in data['results']:
            tmdb_id = item.get('id')
            title = item.get('title', '未知')
            original_title = item.get('original_title', '')
            rating = item.get('vote_average', 0)
            overview = item.get('overview', '')
            poster_path = item.get('poster_path', '')
            
            # 获取详细类型和年份
            detail = fetch_tmdb(f'movie/{tmdb_id}')
            if detail:
                genres = ' / '.join([g['name'] for g in detail.get('genres', [])])
                release_date = detail.get('release_date', '')
                year = release_date[:4] if release_date else ''
            else:
                genres = ''
                year = ''
            
            if movie_exists(tmdb_id):
                print(f'    ⏭️ {title} 已存在')
                continue
            
            movie_data = {
                'title': title,
                'year': year,
                'genre': genres,
                'rating': rating,
                'description': overview[:500],
                'poster': f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else '',
                'video_url': 'https://www.w3schools.com/html/mov_bbb.mp4',
                'douban_id': str(tmdb_id),
                'douban_url': f"https://www.themoviedb.org/movie/{tmdb_id}"
            }
            
            movies.append(movie_data)
            print(f'    ✅ {title} ({year}) ⭐{rating}')
            
            time.sleep(random.uniform(0.3, 0.6))
        
        time.sleep(random.uniform(0.5, 1))
    
    return movies


def crawl_tmdb_popular():
    """抓取 TMDB 热门电影"""
    print(' 从 TMDB 获取热门电影...')
    
    movies = []
    for page in range(1, 5):  # 抓取 4 页，共 80 部
        print(f'   抓取第 {page} 页')
        
        data = fetch_tmdb('movie/popular', {'page': page})
        if not data or 'results' not in data:
            continue
        
        for item in data['results']:
            tmdb_id = item.get('id')
            
            if movie_exists(tmdb_id):
                continue
            
            title = item.get('title', '未知')
            rating = item.get('vote_average', 0)
            overview = item.get('overview', '')
            poster_path = item.get('poster_path', '')
            
            # 获取详细信息
            detail = fetch_tmdb(f'movie/{tmdb_id}')
            if detail:
                genres = ' / '.join([g['name'] for g in detail.get('genres', [])])
                release_date = detail.get('release_date', '')
                year = release_date[:4] if release_date else ''
            else:
                genres = ''
                year = ''
            
            movie_data = {
                'title': title,
                'year': year,
                'genre': genres,
                'rating': rating,
                'description': overview[:500],
                'poster': f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else '',
                'video_url': 'https://www.w3schools.com/html/mov_bbb.mp4',
                'douban_id': str(tmdb_id),
                'douban_url': f"https://www.themoviedb.org/movie/{tmdb_id}"
            }
            
            movies.append(movie_data)
            print(f'    ✅ {title} ({year}) ⭐{rating}')
            
            time.sleep(random.uniform(0.3, 0.6))
        
        time.sleep(random.uniform(0.5, 1))
    
    return movies


def save_to_db(movies):
    print(f'保存 {len(movies)} 部电影到数据库...')
    count = 0
    for movie in movies:
        if movie and movie.get('title'):
            insert_movie(movie)
            count += 1
    print(f'✅ 成功插入 {count} 部')


def main():
    print('=' * 50)
    print('🎬 TMDB 电影爬虫启动')
    print('=' * 50)
    
    all_movies = []
    
    # 抓取高分电影
    top_movies = crawl_tmdb_top_rated()
    all_movies.extend(top_movies)
    
    # 抓取热门电影
    popular_movies = crawl_tmdb_popular()
    all_movies.extend(popular_movies)
    
    # 去重
    seen = set()
    unique = []
    for m in all_movies:
        if m['douban_id'] not in seen:
            seen.add(m['douban_id'])
            unique.append(m)
    
    print(f'\n 共抓取 {len(unique)} 部影片')
    save_to_db(unique)
    
    print('=' * 50)
    print('✅ 完成！')
    print('=' * 50)


if __name__ == '__main__':
    main()