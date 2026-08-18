/**
 * router.js - 页面路由守卫
 * 在需要登录才能访问的页面引入此文件
 */

// 需要登录才能访问的页面列表
const PROTECTED_PAGES = [
    'profile.html',
    // 后续可以添加更多需要登录的页面
];

(function() {
    // 如果当前页面需要登录保护
    const currentPage = window.location.pathname.split('/').pop();
    if (PROTECTED_PAGES.includes(currentPage)) {
        AuthUtil.checkAuth('../auth/login.html');
    }
})();