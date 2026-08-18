from flask import Blueprint, request, jsonify
from models import Database
from utils import decode_token

user_bp = Blueprint('user', __name__, url_prefix='/api/user')

def get_user_id_from_token():
    """从请求头获取用户ID"""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    if not token:
        return None
    user_data = decode_token(token)
    if not user_data:
        return None
    return user_data.get('user_id')


@user_bp.route('/favorites', methods=['GET'])
def get_favorites():
    """获取用户收藏列表"""
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        favorites = Database.execute_query('''
            SELECT m.*, f.created_at as favorited_at 
            FROM favorites f 
            JOIN movies m ON f.movie_id = m.id 
            WHERE f.user_id = %s
            ORDER BY f.created_at DESC
        ''', (user_id,), fetch_all=True)
        
        return jsonify({'success': True, 'data': favorites or []})
    except Exception as e:
        print('获取收藏失败:', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@user_bp.route('/favorites', methods=['POST'])
def toggle_favorite():
    """添加或取消收藏"""
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'message': '请先登录'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
    movie_id = data.get('movie_id')
    if not movie_id:
        return jsonify({'success': False, 'message': '缺少影片ID'}), 400

    try:
        # 检查影片是否存在
        movie = Database.execute_query(
            'SELECT id FROM movies WHERE id = %s',
            (movie_id,), fetch_one=True
        )
        if not movie:
            return jsonify({'success': False, 'message': '影片不存在'}), 404

        # 检查是否已收藏
        existing = Database.execute_query(
            'SELECT id FROM favorites WHERE user_id = %s AND movie_id = %s',
            (user_id, movie_id), fetch_one=True
        )

        if existing:
            # 取消收藏
            Database.execute_query(
                'DELETE FROM favorites WHERE user_id = %s AND movie_id = %s',
                (user_id, movie_id)
            )
            return jsonify({'success': True, 'message': '已取消收藏', 'data': {'favorited': False}})
        else:
            # 添加收藏
            Database.execute_insert(
                'INSERT INTO favorites (user_id, movie_id) VALUES (%s, %s)',
                (user_id, movie_id)
            )
            return jsonify({'success': True, 'message': '收藏成功', 'data': {'favorited': True}})
    except Exception as e:
        print('切换收藏失败:', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@user_bp.route('/history', methods=['GET'])
def get_history():
    """获取观看历史"""
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        history = Database.execute_query('''
            SELECT m.*, h.watched_at 
            FROM history h 
            JOIN movies m ON h.movie_id = m.id 
            WHERE h.user_id = %s
            ORDER BY h.watched_at DESC
            LIMIT 20
        ''', (user_id,), fetch_all=True)
        
        return jsonify({'success': True, 'data': history or []})
    except Exception as e:
        print('获取历史失败:', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@user_bp.route('/history', methods=['POST'])
def add_history():
    """记录观看历史"""
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'message': '请先登录'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
    movie_id = data.get('movie_id')
    if not movie_id:
        return jsonify({'success': False, 'message': '缺少影片ID'}), 400

    try:
        # 检查影片是否存在
        movie = Database.execute_query(
            'SELECT id FROM movies WHERE id = %s',
            (movie_id,), fetch_one=True
        )
        if not movie:
            return jsonify({'success': False, 'message': '影片不存在'}), 404

        # 先删除旧记录（去重）
        Database.execute_query(
            'DELETE FROM history WHERE user_id = %s AND movie_id = %s',
            (user_id, movie_id)
        )
        # 插入新记录
        Database.execute_insert(
            'INSERT INTO history (user_id, movie_id) VALUES (%s, %s)',
            (user_id, movie_id)
        )

        return jsonify({'success': True, 'message': '已记录'})
    except Exception as e:
        print('记录历史失败:', e)
        return jsonify({'success': False, 'message': str(e)}), 500