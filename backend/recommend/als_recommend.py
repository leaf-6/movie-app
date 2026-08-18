"""
als_recommend.py - Spark ALS 协同过滤推荐
"""

import os
import sys
import time
import mysql.connector
import pandas as pd
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, rand, when, desc, row_number
from pyspark.sql.window import Window
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

# ====== 数据库配置 ======
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 改成你的密码
    'database': 'movie_app',
    'charset': 'utf8mb4'
}

# ====== Spark 配置 ======
SPARK_CONFIG = {
    'app_name': 'MovieRecommender',
    'master': 'local[*]',
    'config': {
        'spark.sql.adaptive.enabled': 'true',
        'spark.sql.adaptive.coalescePartitions.enabled': 'true',
        'spark.driver.memory': '2g',
        'spark.executor.memory': '2g'
    }
}


def get_spark_session():
    """获取 Spark Session"""
    builder = SparkSession.builder.appName(SPARK_CONFIG['app_name']).master(SPARK_CONFIG['master'])
    for key, value in SPARK_CONFIG['config'].items():
        builder = builder.config(key, value)
    return builder.getOrCreate()


def load_data_from_mysql(spark):
    """从 MySQL 加载数据"""
    print(" 从 MySQL 加载数据...")
    
    jdbc_url = f"jdbc:mysql://{DB_CONFIG['host']}:3306/{DB_CONFIG['database']}?useSSL=false&serverTimezone=Asia/Shanghai"
    props = {
        'user': DB_CONFIG['user'],
        'password': DB_CONFIG['password'],
        'driver': 'com.mysql.cj.jdbc.Driver'
    }
    
    # 读取历史记录
    history_df = spark.read.jdbc(jdbc_url, 'history', properties=props)
    
    # 读取用户
    users_df = spark.read.jdbc(jdbc_url, 'users', properties=props)
    
    # 读取影片
    movies_df = spark.read.jdbc(jdbc_url, 'movies', properties=props)
    
    print(f"   历史记录: {history_df.count()} 条")
    print(f"   用户: {users_df.count()} 人")
    print(f"   影片: {movies_df.count()} 部")
    
    return history_df, users_df, movies_df


def prepare_training_data(history_df, users_df, movies_df):
    """准备训练数据"""
    print("🔧 准备训练数据...")
    
    # 如果历史记录太少，生成模拟数据
    if history_df.count() < 10:
        print("⚠️ 历史数据不足，生成模拟数据...")
        return generate_synthetic_data(users_df, movies_df)
    
    # 用户观看次数作为评分
    # 按 user_id, movie_id 分组，计算观看次数作为评分
    training_df = history_df.groupBy('user_id', 'movie_id') \
        .count() \
        .withColumnRenamed('count', 'rating') \
        .withColumn('rating', when(col('rating') > 5, 5).otherwise(col('rating')))
    
    print(f"   训练数据: {training_df.count()} 条")
    return training_df


def generate_synthetic_data(users_df, movies_df):
    """生成模拟数据（冷启动）"""
    print("🔧 生成模拟数据...")
    
    # 取用户和影片
    user_ids = users_df.select('id').rdd.flatMap(lambda x: x).collect()
    movie_ids = movies_df.select('id').rdd.flatMap(lambda x: x).collect()
    
    if not user_ids or not movie_ids:
        print("❌ 没有用户或影片数据")
        return None
    
    import random
    spark = get_spark_session()
    
    data = []
    for user_id in user_ids[:20]:  # 最多20个用户
        num_movies = random.randint(3, min(10, len(movie_ids)))
        watched = random.sample(movie_ids, num_movies)
        for movie_id in watched:
            rating = random.randint(3, 5)
            data.append((user_id, movie_id, rating))
    
    df = spark.createDataFrame(data, ['user_id', 'movie_id', 'rating'])
    print(f"   生成模拟数据: {df.count()} 条")
    return df


def train_als_model(training_df):
    """训练 ALS 模型"""
    print(" 训练 ALS 模型...")
    
    als = ALS(
        maxIter=15,
        regParam=0.05,
        rank=10,
        userCol='user_id',
        itemCol='movie_id',
        ratingCol='rating',
        coldStartStrategy='drop',
        implicitPrefs=False,
        nonnegative=True
    )
    
    model = als.fit(training_df)
    print("✅ 模型训练完成")
    return model


def generate_recommendations(model, users_df, movies_df, top_n=10):
    """为所有用户生成推荐"""
    print(f" 生成推荐 (Top-{top_n})...")
    
    # 获取所有用户
    all_users = users_df.select('id').distinct()
    
    # 为每个用户推荐
    recommendations = model.recommendForAllUsers(top_n)
    
    if recommendations.count() == 0:
        print("⚠️ 模型未生成推荐，使用热门影片")
        return get_hot_recommendations(users_df, movies_df, top_n)
    
    # 解析推荐结果
    from pyspark.sql.functions import explode, expr
    
    result_df = recommendations.select(
        col('user_id'),
        explode('recommendations').alias('rec')
    ).select(
        col('user_id'),
        col('rec.movie_id').alias('movie_id'),
        col('rec.rating').alias('predicted_rating')
    )
    
    # 添加排名
    window = Window.partitionBy('user_id').orderBy(desc('predicted_rating'))
    result_df = result_df.withColumn('rank', row_number().over(window))
    
    print(f"   推荐结果: {result_df.count()} 条")
    return result_df


def get_hot_recommendations(users_df, movies_df, top_n=10):
    """冷启动：热门影片推荐"""
    print(" 使用热门影片作为默认推荐...")
    
    # 取评分最高的影片
    top_movies = movies_df.orderBy(desc('rating')).limit(top_n)
    top_movie_ids = top_movies.select('id').rdd.flatMap(lambda x: x).collect()
    
    # 为每个用户推荐相同的影片
    spark = get_spark_session()
    user_ids = users_df.select('id').rdd.flatMap(lambda x: x).collect()
    
    data = []
    for user_id in user_ids:
        for rank, movie_id in enumerate(top_movie_ids, 1):
            data.append((user_id, movie_id, 4.0, rank))
    
    return spark.createDataFrame(data, ['user_id', 'movie_id', 'predicted_rating', 'rank'])


def save_to_mysql(recommendations_df):
    """保存推荐结果到 MySQL"""
    print(" 保存推荐结果到 MySQL...")
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 清空旧推荐
    cursor.execute("DELETE FROM recommendations")
    conn.commit()
    
    # 转换为 Pandas 批量插入
    pdf = recommendations_df.toPandas()
    
    if pdf.empty:
        print("⚠️ 没有推荐数据")
        conn.close()
        return
    
    # 批量插入
    for _, row in pdf.iterrows():
        cursor.execute("""
            INSERT INTO recommendations (user_id, movie_id, predicted_rating, rank)
            VALUES (%s, %s, %s, %s)
        """, (int(row['user_id']), int(row['movie_id']), float(row['predicted_rating']), int(row.get('rank', 0))))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 已保存 {len(pdf)} 条推荐")


def main():
    """主函数"""
    print("=" * 50)
    print("🎬 Spark ALS 推荐系统")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    spark = get_spark_session()
    
    try:
        # 1. 加载数据
        history_df, users_df, movies_df = load_data_from_mysql(spark)
        
        # 2. 准备训练数据
        training_df = prepare_training_data(history_df, users_df, movies_df)
        
        if training_df is None or training_df.count() < 3:
            print("❌ 数据不足，无法训练")
            return
        
        # 3. 训练模型
        model = train_als_model(training_df)
        
        # 4. 生成推荐
        recommendations_df = generate_recommendations(model, users_df, movies_df, top_n=10)
        
        # 5. 保存到 MySQL
        save_to_mysql(recommendations_df)
        
        print("=" * 50)
        print("✅ 推荐系统更新完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 训练失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()


if __name__ == '__main__':
    main()