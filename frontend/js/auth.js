/**
 * auth.js - 认证逻辑（注册/登录/退出）
 * 依赖 storage.js
 */

const AuthUtil = {

    /**
     * 注册新用户
     * @param {string} username
     * @param {string} password
     * @returns {object} { success: boolean, message: string }
     */
    register(username, password) {
        // 校验
        if (!username || username.length < 3) {
            return { success: false, message: '用户名至少3个字符' };
        }
        if (!password || password.length < 6) {
            return { success: false, message: '密码至少6个字符' };
        }

        const users = Storage.getUsers();

        // 检查用户名是否已存在
        if (users.some(u => u.username === username)) {
            return { success: false, message: '用户名已被占用，请换一个' };
        }

        // 保存新用户（密码明文存储，仅用于学习演示）
        users.push({
            username: username,
            password: password,
            createdAt: new Date().toISOString()
        });
        Storage.setUsers(users);

        // 初始化空数据
        Storage.setUserData(username, { favorites: [], history: [] });

        return { success: true, message: ' 注册成功！即将跳转登录...' };
    },

    /**
     * 用户登录
     * @param {string} username
     * @param {string} password
     * @returns {object} { success: boolean, message: string }
     */
    login(username, password) {
        if (!username || !password) {
            return { success: false, message: '请填写完整信息' };
        }

        const users = Storage.getUsers();
        const user = users.find(u => u.username === username);

        if (!user) {
            return { success: false, message: '用户不存在，请先注册' };
        }

        if (user.password !== password) {
            return { success: false, message: '密码错误，请重试' };
        }

        // 保存当前登录状态
        Storage.setCurrentUser({
            username: user.username,
            loginTime: new Date().toISOString()
        });

        return { success: true, message: ' 登录成功！即将跳转...' };
    },

    /**
     * 退出登录
     */
    logout() {
        Storage.clearCurrentUser();
        // 跳转到登录页
        window.location.href = '../auth/login.html';
    },

    /**
     * 检查是否已登录（路由守卫用）
     * @param {string} redirectUrl - 未登录时跳转的地址
     * @returns {boolean}
     */
    checkAuth(redirectUrl) {
        if (!Storage.isLoggedIn()) {
            window.location.href = redirectUrl || '../auth/login.html';
            return false;
        }
        return true;
    },

    /**
     * 获取当前用户名
     */
    getCurrentUsername() {
        const user = Storage.getCurrentUser();
        return user ? user.username : null;
    },

    /**
     * 判断是否已登录
     */
    isLoggedIn() {
        return Storage.isLoggedIn();
    }
};