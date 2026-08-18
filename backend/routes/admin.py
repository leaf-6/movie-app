"""
admin.py - 后台管理 API
"""
from flask import Blueprint, request, jsonify
from models import Database
from utils import decode_token, hash_password, verify_password, generate_token

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# ====== 管理员认证 ======
def verify_admin(token):
    """验证管理员 Token"""
    user_data = decode_token(token)
    if not user_data:
        return None
    # 检查是否是管理员（用户名是 admin 或者有 admin 标识）
    if user_data.get('username') == 'admin':
        return user_data
    return None

# ====== 管理员登录 ======
@admin_bp.route('/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    print(f"🔍 登录尝试: username={username}, password={password}")
    
    admin = Database.execute_query(
        'SELECT * FROM admins WHERE username = %s',
        (username,), fetch_one=True
    )
    
    if not admin:
        return jsonify({'success': False, 'message': '管理员不存在'}), 401
    
    print(f"🔍 数据库密码: {admin['password']}")
    print(f"🔍 输入的密码加密后: {hash_password(password)}")
    print(f"🔍 比对结果: {hash_password(password) == admin['password']}")
    
    if verify_password(password, admin['password']):
        from utils import generate_token
        token = generate_token(admin['id'], admin['username'])
        return jsonify({
            'success': True,
            'data': {'token': token, 'username': admin['username']}
        })
    else:
        return jsonify({'success': False, 'message': '密码错误'}), 401






# ====== 获取统计数据 ======
@admin_bp.route('/stats', methods=['GET'])
def get_stats():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_admin(token):
        return jsonify({'success': False, 'message': '无权限'}), 401
    
    # 统计各类数据
    total_movies = Database.execute_query('SELECT COUNT(*) as count FROM movies', fetch_one=True)
    total_users = Database.execute_query('SELECT COUNT(*) as count FROM users', fetch_one=True)
    total_history = Database.execute_query('SELECT COUNT(*) as count FROM history', fetch_one=True)
    total_favorites = Database.execute_query('SELECT COUNT(*) as count FROM favorites', fetch_one=True)
    
    # 最近7天新增
    week_plays = Database.execute_query('''
        SELECT COUNT(*) as count FROM history 
        WHERE watched_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
    ''', fetch_one=True)
    
    return jsonify({
        'success': True,
        'data': {
            'total_movies': total_movies['count'] if total_movies else 0,
            'total_users': total_users['count'] if total_users else 0,
            'total_history': total_history['count'] if total_history else 0,
            'total_favorites': total_favorites['count'] if total_favorites else 0,
            'week_plays': week_plays['count'] if week_plays else 0
        }
    })

# ====== 获取影片列表（含统计） ======
@admin_bp.route('/movies', methods=['GET'])
def admin_get_movies():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_admin(token):
        return jsonify({'success': False, 'message': '无权限'}), 401
    
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    offset = (page - 1) * limit
    keyword = request.args.get('keyword', '').strip()
    
    if keyword:
        sql = '''
            SELECT m.*, 
                   (SELECT COUNT(*) FROM history h WHERE h.movie_id = m.id) as total_plays,
                   (SELECT COUNT(*) FROM favorites f WHERE f.movie_id = m.id) as total_favs
            FROM movies m
            WHERE m.title LIKE %s
            ORDER BY m.id DESC
            LIMIT %s OFFSET %s
        '''
        params = (f'%{keyword}%', limit, offset)
        count_sql = 'SELECT COUNT(*) as total FROM movies WHERE title LIKE %s'
        count_params = (f'%{keyword}%',)
    else:
        sql = '''
            SELECT m.*, 
                   (SELECT COUNT(*) FROM history h WHERE h.movie_id = m.id) as total_plays,
                   (SELECT COUNT(*) FROM favorites f WHERE f.movie_id = m.id) as total_favs
            FROM movies m
            ORDER BY m.id DESC
            LIMIT %s OFFSET %s
        '''
        params = (limit, offset)
        count_sql = 'SELECT COUNT(*) as total FROM movies'
        count_params = ()
    
    movies = Database.execute_query(sql, params, fetch_all=True)
    total = Database.execute_query(count_sql, count_params, fetch_one=True)
    
    return jsonify({
        'success': True,
        'data': {
            'movies': movies or [],
            'total': total['total'] if total else 0,
            'page': page,
            'limit': limit
        }
    })

# ====== 添加影片 ======
@admin_bp.route('/movies', methods=['POST'])
def admin_add_movie():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_admin(token):
        return jsonify({'success': False, 'message': '无权限'}), 401
    
    data = request.get_json()
    title = data.get('title', '').strip()
    year = data.get('year', '')
    genre = data.get('genre', '')
    rating = data.get('rating', 0)
    description = data.get('description', '')
    poster = data.get('poster', '')
    video_url = data.get('video_url', 'https://www.w3schools.com/html/mov_bbb.mp4')
    
    if not title:
        return jsonify({'success': False, 'message': '请填写影片名称'}), 400
    
    try:
        movie_id = Database.execute_insert('''
            INSERT INTO movies (title, year, genre, rating, description, poster, video_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (title, year, genre, rating, description, poster, video_url))
        
        return jsonify({'success': True, 'message': '添加成功', 'data': {'id': movie_id}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ====== 更新影片 ======
@admin_bp.route('/movies/<int:movie_id>', methods=['PUT'])
def admin_update_movie(movie_id):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_admin(token):
        return jsonify({'success': False, 'message': '无权限'}), 401
    
    data = request.get_json()
    
    try:
        Database.execute_query('''
            UPDATE movies SET 
                title = %s, year = %s, genre = %s, 
                rating = %s, description = %s, poster = %s, video_url = %s
            WHERE id = %s
        ''', (
            data.get('title'), data.get('year'), data.get('genre'),
            data.get('rating'), data.get('description'), data.get('poster'),
            data.get('video_url'), movie_id
        ))
        return jsonify({'success': True, 'message': '更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ====== 删除影片 ======
@admin_bp.route('/movies/<int:movie_id>', methods=['DELETE'])
def admin_delete_movie(movie_id):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_admin(token):
        return jsonify({'success': False, 'message': '无权限'}), 401
    
    try:
        Database.execute_query('DELETE FROM movies WHERE id = %s', (movie_id,))
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ====== 获取用户列表 ======
@admin_bp.route('/users', methods=['GET'])
def admin_get_users():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_admin(token):
        return jsonify({'success': False, 'message': '无权限'}), 401
    
    users = Database.execute_query('''
        SELECT u.*, 
               (SELECT COUNT(*) FROM history h WHERE h.user_id = u.id) as total_watch,
               (SELECT COUNT(*) FROM favorites f WHERE f.user_id = u.id) as total_fav
        FROM users u
        ORDER BY u.id DESC
    ''', fetch_all=True)
    
    return jsonify({'success': True, 'data': users or []})


    # ====== 推荐统计 ======
@admin_bp.route('/recommend/stats', methods=['GET'])
def get_recommend_stats():
    """获取推荐系统统计信息"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_admin(token):
        return jsonify({'success': False, 'message': '无权限'}), 401

    try:
        # 推荐覆盖的用户数
        rec_users = Database.execute_query(
            'SELECT COUNT(DISTINCT user_id) as count FROM recommendations',
            fetch_one=True
        )

        # 总推荐数
        rec_count = Database.execute_query(
            'SELECT COUNT(*) as count FROM recommendations',
            fetch_one=True
        )

        # 总用户数
        total_users = Database.execute_query(
            'SELECT COUNT(*) as count FROM users',
            fetch_one=True
        )

        # 有历史记录的用户数
        active_users = Database.execute_query(
            'SELECT COUNT(DISTINCT user_id) as count FROM history',
            fetch_one=True
        )

        # 推荐覆盖率
        coverage = round((rec_users['count'] / total_users['count'] * 100), 1) if total_users['count'] > 0 else 0

        # 各用户推荐数
        user_recs = Database.execute_query('''
            SELECT 
                u.username,
                COUNT(r.id) as rec_count
            FROM users u
            LEFT JOIN recommendations r ON u.id = r.user_id
            GROUP BY u.id
            ORDER BY rec_count DESC
            LIMIT 20
        ''', fetch_all=True)

        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users['count'] if total_users else 0,
                'active_users': active_users['count'] if active_users else 0,
                'users_with_recs': rec_users['count'] if rec_users else 0,
                'total_recs': rec_count['count'] if rec_count else 0,
                'coverage': coverage,
                'user_recs': user_recs or []
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500