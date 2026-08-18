"""
pure_recommend.py - 纯 Python 协同过滤推荐（使用 PyMySQL）
"""

import pymysql
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 改成你的密码
    'database': 'movie_app',
    'charset': 'utf8mb4'
}


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def load_data():
    """从 MySQL 加载数据"""
    print(" 加载数据...")
    conn = get_connection()
    
    # 用户-影片-评分
    query = """
        SELECT 
            h.user_id,
            h.movie_id,
            COUNT(*) as rating,
            MAX(h.watched_at) as last_watch
        FROM history h
        GROUP BY h.user_id, h.movie_id
    """
    history_df = pd.read_sql(query, conn)
    
    # 用户
    users_df = pd.read_sql("SELECT id, username FROM users", conn)
    
    # 影片
    movies_df = pd.read_sql("SELECT id, title, rating, genre, poster FROM movies", conn)
    
    conn.close()
    
    print(f"   历史记录: {len(history_df)} 条")
    print(f"   用户: {len(users_df)} 人")
    print(f"   影片: {len(movies_df)} 部")
    
    return history_df, users_df, movies_df


def prepare_rating_matrix(history_df, users_df, movies_df):
    """构建用户-影片评分矩阵"""
    print(" 构建评分矩阵...")
    
    if history_df.empty:
        print("⚠️ 没有历史数据，生成模拟数据...")
        return generate_synthetic_data(users_df, movies_df)
    
    pivot = history_df.pivot_table(
        index='user_id',
        columns='movie_id',
        values='rating',
        fill_value=0
    )
    
    print(f"   评分矩阵: {pivot.shape[0]} 用户, {pivot.shape[1]} 影片")
    return pivot


def generate_synthetic_data(users_df, movies_df):
    """生成模拟数据"""
    print("🔧 生成模拟数据...")
    
    import random
    
    user_ids = users_df['id'].tolist()[:20]
    movie_ids = movies_df['id'].tolist()
    
    if not user_ids or not movie_ids:
        print("❌ 没有用户或影片数据")
        return None
    
    data = []
    for user_id in user_ids:
        num = random.randint(3, min(8, len(movie_ids)))
        watched = random.sample(movie_ids, num)
        for movie_id in watched:
            rating = random.randint(3, 5)
            data.append({'user_id': user_id, 'movie_id': movie_id, 'rating': rating})
    
    df = pd.DataFrame(data)
    print(f"   生成 {len(df)} 条模拟数据")
    
    pivot = df.pivot_table(
        index='user_id',
        columns='movie_id',
        values='rating',
        fill_value=0
    )
    
    return pivot


def compute_user_similarity(rating_matrix):
    """计算用户相似度"""
    print(" 计算用户相似度...")
    
    if rating_matrix is None or rating_matrix.empty:
        print("⚠️ 评分矩阵为空")
        return None
    
    user_sim = cosine_similarity(rating_matrix)
    user_sim_df = pd.DataFrame(
        user_sim,
        index=rating_matrix.index,
        columns=rating_matrix.index
    )
    
    print(f"   相似度矩阵: {user_sim_df.shape}")
    return user_sim_df


def generate_recommendations(rating_matrix, user_sim_df, movies_df, top_n=10):
    """为所有用户生成推荐"""
    print(f" 生成推荐 (Top-{top_n})...")
    
    if rating_matrix is None or rating_matrix.empty:
        print("⚠️ 没有评分数据")
        return None
    
    all_recommendations = []
    
    for user_id in rating_matrix.index:
        watched = rating_matrix.loc[user_id]
        watched_movies = watched[watched > 0].index.tolist()
        
        similar_users = user_sim_df[user_id].sort_values(ascending=False).index[1:6]
        
        scores = defaultdict(float)
        for sim_user in similar_users:
            sim_score = user_sim_df.loc[user_id, sim_user]
            if sim_score <= 0:
                continue
            user_watched = rating_matrix.loc[sim_user]
            user_watched_movies = user_watched[user_watched > 0].index.tolist()
            
            for movie_id in user_watched_movies:
                if movie_id not in watched_movies:
                    score = sim_score * user_watched[movie_id]
                    scores[movie_id] += score
        
        sorted_recs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_movie_ids = [m[0] for m in sorted_recs[:top_n]]
        
        if not top_movie_ids:
            top_movie_ids = movies_df.nlargest(top_n, 'rating')['id'].tolist()
        
        for rank, movie_id in enumerate(top_movie_ids, 1):
            all_recommendations.append({
                'user_id': user_id,
                'movie_id': movie_id,
                'rank': rank,
                'score': sorted_recs[rank-1][1] if rank <= len(sorted_recs) else 0
            })
    
    result_df = pd.DataFrame(all_recommendations)
    print(f"   推荐结果: {len(result_df)} 条")
    return result_df


def save_to_mysql(recommendations_df):
    """保存推荐到 MySQL"""
    print(" 保存推荐到 MySQL...")
    
    if recommendations_df is None or recommendations_df.empty:
        print("⚠️ 没有推荐数据")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM recommendations")
    conn.commit()
    
    for _, row in recommendations_df.iterrows():
        cursor.execute("""
            INSERT INTO recommendations (user_id, movie_id, `rank`, predicted_rating)
            VALUES (%s, %s, %s, %s)
        """, (int(row['user_id']), int(row['movie_id']), int(row['rank']), float(row.get('score', 0))))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 已保存 {len(recommendations_df)} 条推荐")


def main():
    print("=" * 50)
    print("🎬 纯 Python 协同过滤推荐")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    history_df, users_df, movies_df = load_data()
    
    rating_matrix = prepare_rating_matrix(history_df, users_df, movies_df)
    
    if rating_matrix is None:
        print("❌ 数据不足，无法生成推荐")
        return
    
    user_sim_df = compute_user_similarity(rating_matrix)
    
    if user_sim_df is None:
        print("❌ 相似度计算失败")
        return
    
    recommendations = generate_recommendations(rating_matrix, user_sim_df, movies_df, top_n=10)
    
    save_to_mysql(recommendations)
    
    print("=" * 50)
    print("✅ 推荐系统更新完成！")
    print("=" * 50)


if __name__ == '__main__':
    main()