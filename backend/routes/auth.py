from flask import Blueprint, request, jsonify
from models import Database
from utils import hash_password, verify_password, generate_token

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def user_register():
    data = request.get_json()
    """用户注册"""
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if len(username) < 3:
        return jsonify({'success': False, 'message': '用户名至少3个字符'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码至少6个字符'}), 400

    # 检查用户是否已存在
    existing = Database.execute_query(
        'SELECT id FROM users WHERE username = %s',
        (username,), fetch_one=True
    )
    if existing:
        return jsonify({'success': False, 'message': '用户名已被占用'}), 400

    # 插入新用户
    hashed_pwd = hash_password(password)
    user_id = Database.execute_insert(
        'INSERT INTO users (username, password) VALUES (%s, %s)',
        (username, hashed_pwd)
    )

    print(f'✅ 新用户注册成功: {username}, ID: {user_id}')  # 加这行调试

    return jsonify({
        'success': True,
        'message': '注册成功',
        'data': {'user_id': user_id, 'username': username}
    })

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': '请填写完整信息'}), 400

    # 查询用户
    user = Database.execute_query(
        'SELECT id, username, password FROM users WHERE username = %s',
        (username,), fetch_one=True
    )

    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    if not verify_password(password, user['password']):
        return jsonify({'success': False, 'message': '密码错误'}), 401

    # 生成 Token
    token = generate_token(user['id'], user['username'])

    return jsonify({
        'success': True,
        'message': '登录成功',
        'data': {
            'token': token,
            'user_id': user['id'],
            'username': user['username']
        }
    })

@auth_bp.route('/register', methods=['POST'])
def register():
    # ... 原有注册逻辑 ...

    # 注册成功后，自动推荐热门影片
    if user_id:
        # 获取热门影片
        hot_movies = Database.execute_query(
            'SELECT id FROM movies ORDER BY rating DESC LIMIT 5',
            fetch_all=True
        )

        # 为新手用户生成模拟历史（可选）
        for m in hot_movies or []:
            Database.execute_query(
                'INSERT IGNORE INTO history (user_id, movie_id) VALUES (%s, %s)',
                (user_id, m['id'])
            )

    return jsonify({
        'success': True,
        'message': '注册成功',
        'data': {'user_id': user_id, 'username': username}
    })