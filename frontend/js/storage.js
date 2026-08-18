/**
 * storage.js - localStorage 操作封装
 * 所有数据读写统一走这里，方便后期替换成后端API
 */

const Storage = {

    // ---------- 用户相关 ----------
    getUsers() {
        return JSON.parse(localStorage.getItem('movie_users')) || [];
    },

    setUsers(users) {
        localStorage.setItem('movie_users', JSON.stringify(users));
    },

    getCurrentUser() {
        const data = JSON.parse(localStorage.getItem('movie_current_user'));
        return data || null;
    },

    setCurrentUser(user) {
        localStorage.setItem('movie_current_user', JSON.stringify(user));
    },

    clearCurrentUser() {
        localStorage.removeItem('movie_current_user');
    },

    // ---------- 用户数据（收藏/历史） ----------
    getUserData(username) {
        const key = `movie_userdata_${username}`;
        const data = JSON.parse(localStorage.getItem(key));
        return data || { favorites: [], history: [] };
    },

    setUserData(username, data) {
        const key = `movie_userdata_${username}`;
        localStorage.setItem(key, JSON.stringify(data));
    },

    // ---------- 通用 ----------
    isLoggedIn() {
        return this.getCurrentUser() !== null;
    }
};