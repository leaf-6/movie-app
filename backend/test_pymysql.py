import pymysql
import time

print("🔌 使用 PyMySQL 测试连接...")

config = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 改成你的 MySQL 密码
    'database': 'movie_app',
    'charset': 'utf8mb4',
    'connect_timeout': 5
}

print(f"  尝试连接...")

try:
    start = time.time()
    conn = pymysql.connect(**config)
    elapsed = time.time() - start
    print(f"✅ 连接成功！耗时 {elapsed:.2f} 秒")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM movies")
    result = cursor.fetchone()
    print(f"  📊 movies 表: {result[0]} 条")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    result = cursor.fetchone()
    print(f"  📊 users 表: {result[0]} 条")
    
    cursor.execute("SELECT COUNT(*) FROM history")
    result = cursor.fetchone()
    print(f"  📊 history 表: {result[0]} 条")
    
    conn.close()
    print("✅ 测试完成")
    
except pymysql.Error as e:
    print(f"❌ 连接失败: {e}")
    print("\n💡 提示: 检查 MySQL 密码是否正确")
    print("   如果不知道密码，尝试把密码改为空字符串 ''")
except Exception as e:
    print(f"❌ 其他错误: {e}")