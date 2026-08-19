// ==================== 最终版 api.js ====================
// 自动判断环境：本地用 localhost，手机用局域网 IP
// 你只需要把下面的 IP 换成你电脑的局域网 IP

// ⚠️ 在这里填你电脑的局域网 IP（在终端输入 ipconfig 查看）
const YOUR_LOCAL_IP = '192.168.10.37';

// 自动判断：如果是手机访问，用 IP；如果是电脑访问，用 localhost
const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

let API_BASE;
if (isLocal) {
    // 电脑本地访问：用 localhost
    API_BASE = 'http://localhost:5000/api';
} else if (isMobile) {
    // 手机访问：用局域网 IP（确保手机和电脑在同一个 WiFi）
    API_BASE = `http://${YOUR_LOCAL_IP}:5000/api`;
} else {
    // 其他情况（比如部署到 Netlify）：也用局域网 IP
    API_BASE = `http://${YOUR_LOCAL_IP}:5000/api`;
}

// ==================== 以下代码保持不变 ====================
function getToken() {
    return localStorage.getItem('movie_token');
}

function setToken(token) {
    localStorage.setItem('movie_token', token);
}

function clearToken() {
    localStorage.removeItem('movie_token');
}

async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers
    };

    try {
        const response = await fetch(url, config);
        const data = await response.json();

        if (response.status === 401) {
            clearToken();
            const currentPage = window.location.pathname.split('/').pop();
            if (!['login.html', 'register.html'].includes(currentPage)) {
                window.location.href = '../auth/login.html';
            }
        }

        return data;
    } catch (error) {
        console.error('API 请求失败:', error);
        return { success: false, message: '网络连接失败，请检查后端服务是否运行' };
    }
}

// ==================== 认证相关 ====================
export const AuthAPI = {
    register(username, password) {
        return request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },

    login(username, password) {
        return request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },

    isLoggedIn() {
        return !!getToken();
    },

    getCurrentUser() {
        const username = localStorage.getItem('movie_username');
        return username ? { username } : null;
    },

    setUserInfo(username, token) {
        setToken(token);
        localStorage.setItem('movie_username', username);
    },

    logout() {
        clearToken();
        localStorage.removeItem('movie_username');
        window.location.href = '../auth/login.html';
    }
};

// ==================== 影片相关 ====================
export const MovieAPI = {
    getMovies(keyword = '', page = 1, limit = 20, sort = '') {
        const params = new URLSearchParams({ page, limit });
        if (keyword) params.append('keyword', keyword);
        if (sort) params.append('sort', sort);
        return request(`/movies?${params.toString()}`);
    },

    getMovieDetail(id) {
        return request(`/movies/${id}`);
    },

    getRecommendations() {
        return request('/movies/recommend');
    },

    filterMovies(params) {
        return request('/movies/filter', {
            method: 'POST',
            body: JSON.stringify(params)
        });
    },

    rateMovie(movieId, rating) {
        return request(`/movies/${movieId}/rating`, {
            method: 'POST',
            body: JSON.stringify({ rating })
        });
    },

    getUserRating(movieId) {
        return request(`/movies/${movieId}/rating`);
    }
};

// ==================== 用户相关 ====================
export const UserAPI = {
    getFavorites() {
        return request('/user/favorites');
    },

    toggleFavorite(movieId) {
        return request('/user/favorites', {
            method: 'POST',
            body: JSON.stringify({ movie_id: movieId })
        });
    },

    getHistory() {
        return request('/user/history');
    },

    addHistory(movieId) {
        return request('/user/history', {
            method: 'POST',
            body: JSON.stringify({ movie_id: movieId })
        });
    }
};

// ==================== 弹幕相关 ====================
export const DanmakuAPI = {
    getDanmaku(movieId) {
        return request(`/danmaku/${movieId}`);
    },

    sendDanmaku(movieId, content, time, color = '#ffffff', size = 'medium') {
        return request('/danmaku', {
            method: 'POST',
            body: JSON.stringify({ movie_id: movieId, content, time, color, size })
        });
    }
};

console.log('✅ API 已就绪，当前后端地址:', API_BASE);