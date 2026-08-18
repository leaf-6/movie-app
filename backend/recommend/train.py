"""
train.py - Spark ALS 推荐模型训练
"""
import os
import sys
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, when, rand
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
import mysql.connector

# ====== 数据库配置 ======
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 改成你的密码
    'database': 'movie_app',
    'charset': 'utf8mb4'
}

def get_spark_session():
    """获取 Spark Session"""
    return SparkSession.builder \
        .appName("MovieRecommender") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()

def load_data_from_mysql(spark):
    """从 MySQL 加载用户-影片交互数据"""
    print(" 从 MySQL 加载历史数据...")
    
    # 读取历史记录
    history_df = spark.read.format("jdbc") \
        .option("url", f"jdbc:mysql://{DB_CONFIG['host']}:3306/{DB_CONFIG['database']}?useSSL=false") \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .option("dbtable", "history") \
        .option("user", DB_CONFIG['user']) \
        .option("password", DB_CONFIG['password']) \
        .load()
    
    # 读取影片数据（获取影片ID）
    movies_df = spark.read.format("jdbc") \
        .option("url", f"jdbc:mysql://{DB_CONFIG['host']}:3306/{DB_CONFIG['database']}?useSSL=false") \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .option("dbtable", "movies") \
        .option("user", DB_CONFIG['user']) \
        .option("password", DB_CONFIG['password']) \
        .load()
    
    # 获取所有用户 ID
    users_df = spark.read.format("jdbc") \
        .option("url", f"jdbc:mysql://{DB_CONFIG['host']}:3306/{DB_CONFIG['database']}?useSSL=false") \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .option("dbtable", "users") \
        .option("user", DB_CONFIG['user']) \
        .option("password", DB_CONFIG['password']) \
        .load()
    
    print(f"   历史记录: {history_df.count()} 条")
    print(f"   影片: {movies_df.count()} 部")
    print(f"   用户: {users_df.count()} 人")
    
    return history_df, movies_df, users_df

def generate_training_data(history_df, users_df, movies_df):
    """生成训练数据（用户-影片-评分）"""
    print(" 生成训练数据...")
    
    # 如果历史记录为空，生成模拟数据
    if history_df.count() == 0:
        print("⚠️ 没有历史数据，生成模拟数据用于训练...")
        return generate_synthetic_data(users_df, movies_df)
    
    # 为历史记录添加评分（观看即视为 4.0 分，可优化）
    # 这里用随机评分模拟用户偏好（实际可用收藏、观看时长等加权）
    training_df = history_df.select(
        col("user_id"),
        col("movie_id"),
        # 模拟评分：3.5-5.0 之间，观看多次的评分更高
        (lit(3.5) + rand() * 1.5).alias("rating")
    ).distinct()
    
    print(f"   训练数据: {training_df.count()} 条")
    return training_df

def generate_synthetic_data(users_df, movies_df):
    """生成模拟评分数据（冷启动）"""
    from pyspark.sql.functions import explode, array, lit, rand, round as spark_round
    
    # 取前 20 个用户和所有影片
    user_ids = users_df.select("id").limit(20).rdd.flatMap(lambda x: x).collect()
    movie_ids = movies_df.select("id").rdd.flatMap(lambda x: x).collect()
    
    if not user_ids or not movie_ids:
        print("❌ 没有用户或影片数据，无法生成模拟数据")
        return None
    
    # 生成模拟评分（每个用户随机看 5-15 部影片）
    import random
    data = []
    for user_id in user_ids:
        # 每个用户看 5-15 部
        num_movies = random.randint(5, min(15, len(movie_ids)))
        watched = random.sample(movie_ids, num_movies)
        for movie_id in watched:
            rating = round(random.uniform(3.0, 5.0), 1)
            data.append((user_id, movie_id, rating))
    
    # 创建 Spark DataFrame
    spark = get_spark_session()
    df = spark.createDataFrame(data, ["user_id", "movie_id", "rating"])
    
    print(f"   生成模拟数据: {df.count()} 条")
    return df

def train_als_model(training_df):
    """训练 ALS 模型"""
    print(" 训练 ALS 模型...")
    
    als = ALS(
        maxIter=10,
        regParam=0.01,
        userCol="user_id",
        itemCol="movie_id",
        ratingCol="rating",
        coldStartStrategy="drop",
        implicitPrefs=False  # 显式评分
    )
    
    model = als.fit(training_df)
    print("✅ 模型训练完成")
    return model

def generate_recommendations(model, users_df, movies_df):
    """为所有用户生成 Top-N 推荐"""
    print(" 生成推荐结果...")
    
    # 获取所有用户
    all_users = users_df.select("id").distinct()
    
    # 为每个用户推荐 Top 10
    recommendations = model.recommendForAllUsers(10)
    
    if recommendations.count() == 0:
        print("⚠️ 没有生成推荐，使用默认推荐")
        return get_default_recommendations(users_df, movies_df)
    
    # 解析推荐结果
    from pyspark.sql.functions import explode, col, struct, expr
    
    # 展开推荐列表
    result_df = recommendations.select(
        col("user_id"),
        explode("recommendations").alias("rec")
    ).select(
        col("user_id"),
        col("rec.movie_id").alias("movie_id"),
        col("rec.rating").alias("predicted_rating")
    )
    
    print(f"   推荐结果: {result_df.count()} 条")
    return result_df

def get_default_recommendations(users_df, movies_df):
    """冷启动默认推荐（热门影片）"""
    print(" 使用默认推荐（热门影片）...")
    
    # 取前 10 部评分最高的影片
    top_movies = movies_df.orderBy(col("rating").desc()).limit(10)
    
    # 为每个用户推荐相同的 Top 10
    from pyspark.sql.functions import explode, array, lit
    
    # 获取所有用户 ID
    user_ids = users_df.select("id").rdd.flatMap(lambda x: x).collect()
    movie_ids = top_movies.select("id").rdd.flatMap(lambda x: x).collect()
    
    data = []
    for user_id in user_ids:
        for movie_id in movie_ids:
            data.append((user_id, movie_id, 4.0))
    
    spark = get_spark_session()
    return spark.createDataFrame(data, ["user_id", "movie_id", "predicted_rating"])

def save_to_mysql(recommendations_df):
    """保存推荐结果到 MySQL"""
    print(" 保存推荐结果到 MySQL...")
    
    # 先删除旧的推荐表
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS recommendations")
    cursor.execute("""
        CREATE TABLE recommendations (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            movie_id INT NOT NULL,
            predicted_rating DECIMAL(5,2),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
            UNIQUE KEY unique_recommend (user_id, movie_id)
        )
    """)
    conn.commit()
    conn.close()
    
    # 转换为 Pandas 并批量插入
    pdf = recommendations_df.toPandas()
    
    if pdf.empty:
        print("⚠️ 没有推荐数据")
        return
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    for _, row in pdf.iterrows():
        cursor.execute("""
            INSERT IGNORE INTO recommendations (user_id, movie_id, predicted_rating)
            VALUES (%s, %s, %s)
        """, (int(row['user_id']), int(row['movie_id']), float(row['predicted_rating'])))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 已保存 {len(pdf)} 条推荐")

def main():
    """主函数"""
    print("=" * 50)
    print(" Spark 推荐系统训练")
    print("=" * 50)
    
    spark = get_spark_session()
    
    try:
        # 1. 加载数据
        history_df, movies_df, users_df = load_data_from_mysql(spark)
        
        # 2. 生成训练数据
        training_df = generate_training_data(history_df, users_df, movies_df)
        
        if training_df is None or training_df.count() < 3:
            print("❌ 数据不足，无法训练")
            return
        
        # 3. 训练模型
        model = train_als_model(training_df)
        
        # 4. 生成推荐
        recommendations_df = generate_recommendations(model, users_df, movies_df)
        
        # 5. 保存到 MySQL
        save_to_mysql(recommendations_df)
        
        print("=" * 50)
        print("✅ 推荐系统训练完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 训练失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()

if __name__ == "__main__":
    main()