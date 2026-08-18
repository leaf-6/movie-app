from flask import Flask
from flask_cors import CORS
from config import Config

from routes.auth import auth_bp
from routes.movies import movies_bp
from routes.user import user_bp

from routes.admin import admin_bp
from routes.danmaku import danmaku_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.JWT_SECRET_KEY

# ====== 修改这里：允许所有来源（开发环境） ======
CORS(app, origins=['http://localhost:5500', 'http://127.0.0.1:5500', '*'], supports_credentials=True)

# 注册路由
app.register_blueprint(auth_bp)
app.register_blueprint(movies_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(danmaku_bp)

@app.route('/api/health', methods=['GET'])
def health():
    return {'status': 'ok', 'message': '我的影视 API 运行中'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)