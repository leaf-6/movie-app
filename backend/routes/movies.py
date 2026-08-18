from flask import Blueprint, request, jsonify
from models import Database
from utils import decode_token

movies_bp = Blueprint('movies', __name__, url_prefix='/api/movies')

@movies_bp.route('', methods=['GET'])
def get_movies():
    """获取影片列表（支持搜索、排序、分页）"""
    keyword = request.args.get('keyword', '').strip()
    sort = request.args.get('sort', '')  # 新增排序参数
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    offset = (page - 1) * limit

    # 排序字段映射
    sort_map = {
        'hot': 'play_count DESC, rating DESC',  # 热播：按播放量+评分
        'rating': 'rating DESC',
        'year': 'year DESC',
        'title': 'title ASC'
    }
    order_by = sort_map.get(sort, 'rating DESC')

    if keyword:
        sql = f'''
            SELECT m.*, 
                   (SELECT COUNT(*) FROM history h WHERE h.movie_id = m.id) as play_count,
                   (SELECT COUNT(*) FROM favorites f WHERE f.movie_id = m.id) as fav_count
            FROM movies m
            WHERE m.title LIKE %s OR m.genre LIKE %s
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
        '''
        params = (f'%{keyword}%', f'%{keyword}%', limit, offset)
        count_sql = 'SELECT COUNT(*) as total FROM movies WHERE title LIKE %s OR genre LIKE %s'
        count_params = (f'%{keyword}%', f'%{keyword}%')
    else:
        sql = f'''
            SELECT m.*, 
                   (SELECT COUNT(*) FROM history h WHERE h.movie_id = m.id) as play_count,
                   (SELECT COUNT(*) FROM favorites f WHERE f.movie_id = m.id) as fav_count
            FROM movies m
            ORDER BY {order_by}
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

@movies_bp.route('/<int:movie_id>', methods=['GET'])
def get_movie_detail(movie_id):
    """获取单部影片详情"""
    movie = Database.execute_query(
        'SELECT * FROM movies WHERE id = %s',
        (movie_id,), fetch_one=True
    )

    if not movie:
        return jsonify({'success': False, 'message': '影片不存在'}), 404

    return jsonify({
        'success': True,
        'data': movie
    })

@movies_bp.route('/recommend', methods=['GET'])

def get_recommendations():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_data = decode_token(token)

    if not user_data:
        # 未登录：返回热门影片
        movies = Database.execute_query(
            'SELECT * FROM movies ORDER BY rating DESC LIMIT 6',
            fetch_all=True
        )
        return jsonify({'success': True, 'data': movies or []})

    user_id = user_data['user_id']

    # 检查用户是否有历史记录
    history = Database.execute_query(
        'SELECT COUNT(*) as count FROM history WHERE user_id = %s',
        (user_id,), fetch_one=True
    )

    if not history or history['count'] == 0:
        # 冷启动：返回热门影片 + 随机推荐
        movies = Database.execute_query(
            'SELECT * FROM movies ORDER BY rating DESC LIMIT 6',
            fetch_all=True
        )
        return jsonify({'success': True, 'data': movies or []})

    # 有历史记录：使用协同过滤推荐
    recs = Database.execute_query('''
        SELECT m.*, r.predicted_rating
        FROM recommendations r
        JOIN movies m ON r.movie_id = m.id
        WHERE r.user_id = %s
        ORDER BY r.rank ASC
        LIMIT 8
    ''', (user_id,), fetch_all=True)

    if recs:
        return jsonify({'success': True, 'data': recs})

    # 降级：返回热门
    movies = Database.execute_query(
        'SELECT * FROM movies ORDER BY rating DESC LIMIT 6',
        fetch_all=True
    )
    return jsonify({'success': True, 'data': movies or []})

@movies_bp.route('/filter', methods=['POST'])
def filter_movies():
    data = request.get_json()
    genre = data.get('genre', '')
    year_start = data.get('year_start', '')
    year_end = data.get('year_end', '')
    sort = data.get('sort', 'rating')
    sort_order = data.get('sort_order', 'DESC')
    page = data.get('page', 1)
    limit = data.get('limit', 20)
    offset = (page - 1) * limit
    
    conditions = []
    params = []
    
    if genre:
        conditions.append('genre LIKE %s')
        params.append(f'%{genre}%')
    
    if year_start:
        conditions.append('year >= %s')
        params.append(year_start)
    
    if year_end:
        conditions.append('year <= %s')
        params.append(year_end)
    
    where_clause = ' AND '.join(conditions) if conditions else '1=1'
    
    # 排序字段映射
    sort_map = {
        'hot': 'play_count DESC, rating DESC',
        'rating': 'rating DESC',
        'year': 'year DESC',
        'title': 'title ASC'
    }
    order_by = sort_map.get(sort, 'rating DESC')
    
    sql = f'''
        SELECT m.*, 
               (SELECT COUNT(*) FROM history h WHERE h.movie_id = m.id) as play_count,
               (SELECT COUNT(*) FROM favorites f WHERE f.movie_id = m.id) as fav_count
        FROM movies m
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
    '''
    params.extend([limit, offset])
    
    count_sql = f'SELECT COUNT(*) as total FROM movies WHERE {where_clause}'
    
    movies = Database.execute_query(sql, params, fetch_all=True)
    total = Database.execute_query(count_sql, params[:-2], fetch_one=True)
    
    return jsonify({
        'success': True,
        'data': {
            'movies': movies or [],
            'total': total['total'] if total else 0,
            'page': page,
            'limit': limit
        }
    }) 


# ====== 评分相关 ======

@movies_bp.route('/<int:movie_id>/rating', methods=['GET'])
def get_user_rating(movie_id):
    """获取当前用户对影片的评分"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_data = decode_token(token)
    
    if not user_data:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    user_id = user_data['user_id']
    
    rating = Database.execute_query('''
        SELECT rating FROM user_ratings
        WHERE user_id = %s AND movie_id = %s
    ''', (user_id, movie_id), fetch_one=True)
    
    return jsonify({
        'success': True,
        'data': {'rating': rating['rating'] if rating else 0}
    })


@movies_bp.route('/<int:movie_id>/rating', methods=['POST'])
def rate_movie(movie_id):
    """给影片评分"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_data = decode_token(token)
    
    if not user_data:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    user_id = user_data['user_id']
    data = request.get_json()
    rating = data.get('rating', 0)
    
    if rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': '评分必须在 1-5 之间'}), 400
    
    try:
        # 插入或更新评分
        Database.execute_query('''
            INSERT INTO user_ratings (user_id, movie_id, rating)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE rating = %s, updated_at = CURRENT_TIMESTAMP
        ''', (user_id, movie_id, rating, rating))
        
        # 重新计算平均分
        stats = Database.execute_query('''
            SELECT 
                ROUND(AVG(rating), 2) as avg_rating,
                COUNT(*) as rating_count
            FROM user_ratings
            WHERE movie_id = %s
        ''', (movie_id,), fetch_one=True)
        
        # 更新 movies 表
        Database.execute_query('''
            UPDATE movies 
            SET avg_rating = %s, rating_count = %s
            WHERE id = %s
        ''', (stats['avg_rating'] or 0, stats['rating_count'] or 0, movie_id))
        
        return jsonify({
            'success': True,
            'message': '评分成功',
            'data': {
                'user_rating': rating,
                'avg_rating': stats['avg_rating'] or 0,
                'rating_count': stats['rating_count'] or 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500