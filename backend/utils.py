import hashlib
import jwt
from datetime import datetime, timedelta
from config import Config

def hash_password(password):
    """密码加密（使用 SHA256）"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """验证密码"""
    return hash_password(password) == hashed

def generate_token(user_id, username):
    """生成 JWT Token"""
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')

def decode_token(token):
    """解析 JWT Token"""
    try:
        return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
    except:
        return None