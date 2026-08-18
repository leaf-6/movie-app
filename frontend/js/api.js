/**
 * api.js - 后端 API 调用封装
 * 所有后端请求统一走这里
 */

// 后端地址（根据实际情况修改）
const API_BASE = 'http://localhost:5000/api';

// 获取存储的 Token
function getToken() {
    return localStorage.getItem('movie_token');
}

// 保存 Token
function setToken(token) {
    localStorage.setItem('movie_token', token);
}

// 清除 Token
function clearToken() {
    localStorage.removeItem('movie_token');
}

// 通用请求函数
async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    // 如果有 Token，添加到请求头
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
        
        // 如果返回 401 未授权，清除本地 Token
        if (response.status === 401) {
            clearToken();
            // 如果当前页面不是登录/注册页，跳转登录
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
    // 注册
    register(username, password) {
        return request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },

    // 登录
    login(username, password) {
        return request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },

    // 是否已登录（有 Token 就算已登录）
    isLoggedIn() {
        return !!getToken();
    },

    // 获取当前用户信息（从 Token 解析，暂不实现完整解析）
    getCurrentUser() {
        // 简单版：只返回是否登录，用户名需要从登录响应中保存
        const username = localStorage.getItem('movie_username');
        return username ? { username } : null;
    },

    // 保存用户信息
    setUserInfo(username, token) {
        setToken(token);
        localStorage.setItem('movie_username', username);
    },

    // 退出登录
    logout() {
        clearToken();
        localStorage.removeItem('movie_username');
        window.location.href = '../auth/login.html';
    }
};

// ==================== 影片相关 ====================

export const MovieAPI = {
    // 获取影片列表（支持搜索、分页、排序）
    getMovies(keyword = '', page = 1, limit = 20, sort = '') {
        const params = new URLSearchParams({ page, limit });
        if (keyword) params.append('keyword', keyword);
        if (sort) params.append('sort', sort);
        return request(`/movies?${params.toString()}`);
    },

    // 获取单部影片详情
    getMovieDetail(id) {
        return request(`/movies/${id}`);
    },

    // 获取推荐影片
    getRecommendations() {
        return request('/movies/recommend');
    }
};

// ==================== 用户相关 ====================
export const UserAPI = {
    // 获取收藏列表
    getFavorites() {
        return request('/user/favorites');
    },

    // 切换收藏状态（添加或取消）
    toggleFavorite(movieId) {
        return request('/user/favorites', {
            method: 'POST',
            body: JSON.stringify({ movie_id: movieId })
        });
    },

    // 获取观看历史
    getHistory() {
        return request('/user/history');
    },

    // 记录观看历史
    addHistory(movieId) {
        return request('/user/history', {
            method: 'POST',
            body: JSON.stringify({ movie_id: movieId })
        });
    }
};