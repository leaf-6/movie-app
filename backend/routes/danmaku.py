"""
danmaku.py - 弹幕 API
"""
from flask import Blueprint, request, jsonify
from models import Database
from utils import decode_token

danmaku_bp = Blueprint('danmaku', __name__, url_prefix='/api/danmaku')

def get_user_id_from_token():
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    if not token:
        return None
    user_data = decode_token(token)
    if not user_data:
        return None
    return user_data.get('user_id')

def get_username_from_token():
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    if not token:
        return None
    user_data = decode_token(token)
    if not user_data:
        return None
    return user_data.get('username')


@danmaku_bp.route('/<int:movie_id>', methods=['GET'])
def get_danmaku(movie_id):
    """获取影片的所有弹幕"""
    try:
        danmaku = Database.execute_query('''
            SELECT id, user_id, username, content, time, color, size, created_at
            FROM danmaku
            WHERE movie_id = %s
            ORDER BY time ASC
        ''', (movie_id,), fetch_all=True)
        
        return jsonify({'success': True, 'data': danmaku or []})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@danmaku_bp.route('', methods=['POST'])
def send_danmaku():
    """发送弹幕"""
    data = request.get_json()
    movie_id = data.get('movie_id')
    content = data.get('content', '').strip()
    time = data.get('time', 0)
    color = data.get('color', '#ffffff')
    size = data.get('size', 'medium')
    
    if not movie_id:
        return jsonify({'success': False, 'message': '缺少影片ID'}), 400
    
    if not content:
        return jsonify({'success': False, 'message': '弹幕内容不能为空'}), 400
    
    if len(content) > 200:
        return jsonify({'success': False, 'message': '弹幕内容太长（最多200字）'}), 400
    
    # 获取用户信息
    user_id = get_user_id_from_token()
    username = get_username_from_token()
    
    if not username:
        username = '匿名'
    
    try:
        danmaku_id = Database.execute_insert('''
            INSERT INTO danmaku (movie_id, user_id, username, content, time, color, size)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (movie_id, user_id, username, content, time, color, size))
        
        return jsonify({
            'success': True,
            'message': '弹幕发送成功',
            'data': {
                'id': danmaku_id,
                'username': username,
                'content': content,
                'time': time,
                'color': color,
                'size': size
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500