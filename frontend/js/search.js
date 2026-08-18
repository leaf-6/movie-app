/**
 * search.js - 搜索功能核心逻辑
 * 依赖 data.js (window.mockMovies)
 */

(function() {
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearBtn');
    const resultGrid = document.getElementById('resultGrid');
    const resultCount = document.getElementById('resultCount');
    const statsArea = document.getElementById('statsArea');
    const resultsArea = document.getElementById('resultsArea');

    const allMovies = window.mockMovies || [];

    // ---------- 渲染搜索结果 ----------
    function renderResults(movies) {
        if (movies.length === 0) {
            // 空状态：显示推荐
            resultGrid.innerHTML = `
                    <div class="empty-state" style="grid-column:1/-1;">
                        <div class="icon">🔍</div>
                        <h2>未找到相关影片</h2>
                        <p>试试其他关键词，或者看看大家正在看什么</p>
                        <div class="hot-recommend">
                            <h3>🔥 热门推荐</h3>
                            <div class="movie-grid" id="recommendGrid"></div>
                        </div>
                    </div>
                `;
            // 在空状态里渲染推荐影片（取前4部）
            const recommendGrid = document.getElementById('recommendGrid');
            if (recommendGrid) {
                const top4 = allMovies.slice(0, 4);
                recommendGrid.innerHTML = top4.map((m, idx) => `
                        <div class="movie-card" onclick="location.href='player.html?id=${idx}'">
                            <img src="${m.poster}" alt="${m.title}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22280%22%3E%3Crect fill=%22%23222%22 width=%22200%22 height=%22280%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23666%22 font-size=%2220%22%3E🎬%3C/text%3E%3C/svg%3E'" />
                            <div class="info">
                                <h3>${m.title}</h3>
                                <div class="meta">
                                    <span>${m.year}</span>
                                    <span class="rating">⭐ ${m.rating}</span>
                                </div>
                            </div>
                        </div>
                    `).join('');
            }
            statsArea.style.display = 'none';
            return;
        }

        statsArea.style.display = 'block';
        resultCount.textContent = movies.length;

        resultGrid.innerHTML = movies.map((m, idx) => {
            // 找到在原数组中的真实索引（用于跳转 player.html?id=真实索引）
            const realIndex = allMovies.indexOf(m);
            return `
                    <div class="movie-card" onclick="location.href='player.html?id=${realIndex}'">
                        <img src="${m.poster}" alt="${m.title}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22280%22%3E%3Crect fill=%22%23222%22 width=%22200%22 height=%22280%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23666%22 font-size=%2220%22%3E🎬%3C/text%3E%3C/svg%3E'" />
                        <div class="info">
                            <h3>${m.title}</h3>
                            <div class="meta">
                                <span>${m.year}</span>
                                <span>${m.genre || '未知'}</span>
                                <span class="rating">⭐ ${m.rating}</span>
                            </div>
                        </div>
                    </div>
                `;
        }).join('');
    }

    // ---------- 执行搜索 ----------
    function doSearch(keyword) {
        const trimmed = keyword.trim();

        if (!trimmed) {
            // 空关键词：显示全部
            renderResults(allMovies);
            clearBtn.classList.remove('show');
            return;
        }

        clearBtn.classList.add('show');

        // 模糊匹配：标题包含 或 类型包含
        const lower = trimmed.toLowerCase();
        const filtered = allMovies.filter(m =>
            m.title.toLowerCase().includes(lower) ||
            (m.genre && m.genre.toLowerCase().includes(lower))
        );

        renderResults(filtered);
    }

    // ---------- 清空搜索 ----------
    function clearSearch() {
        searchInput.value = '';
        clearBtn.classList.remove('show');
        renderResults(allMovies);
        searchInput.focus();
    }

    // ---------- 事件绑定 ----------
    // 1. 输入时实时搜索（防抖）
    let debounceTimer = null;
    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            doSearch(this.value);
        }, 200);
    });

    // 2. 点击搜索图标
    document.getElementById('searchIcon').addEventListener('click', function() {
        doSearch(searchInput.value);
    });

    // 3. 按回车搜索
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            doSearch(this.value);
        }
        if (e.key === 'Escape') {
            clearSearch();
        }
    });

    // 4. 清空按钮
    clearBtn.addEventListener('click', clearSearch);

    // ---------- 初始化：显示全部 ----------
    renderResults(allMovies);
    statsArea.style.display = 'block';
    resultCount.textContent = allMovies.length;

})();