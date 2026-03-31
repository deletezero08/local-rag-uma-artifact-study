/**
 * Utility functions for MemoraRAG
 * 纯工具函数，不依赖 DOM 或 Store
 */

/**
 * 防抖函数
 */
export function debounce(fn, delay) {
    let timer = null;
    return function (...args) {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

/**
 * 节流函数
 */
export function throttle(fn, limit) {
    let inThrottle;
    return function (...args) {
        if (!inThrottle) {
            fn.apply(this, args);
            inThrottle = true;
            setTimeout(() => (inThrottle = false), limit);
        }
    };
}

/**
 * HTML 转义，防止 XSS
 */
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 格式化时间戳 (s) -> MM-DD HH:mm
 */
export function formatTimestamp(ts) {
    const dt = new Date(ts * 1000);
    return `${(dt.getMonth() + 1).toString().padStart(2, '0')}-${dt.getDate().toString().padStart(2, '0')} ${dt.getHours().toString().padStart(2, '0')}:${dt.getMinutes().toString().padStart(2, '0')}`;
}

/**
 * 获取文件后缀图标类名
 */
export function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const map = {
        'pdf': 'fa-file-pdf',
        'docx': 'fa-file-word',
        'doc': 'fa-file-word',
        'txt': 'fa-file-lines',
        'md': 'fa-brands fa-markdown',
        'yml': 'fa-file-code',
        'yaml': 'fa-file-code',
        'csv': 'fa-file-csv',
        'html': 'fa-file-code',
        'htm': 'fa-file-code',
        'png': 'fa-solid fa-image',
        'jpg': 'fa-solid fa-image',
        'jpeg': 'fa-solid fa-image',
        'webp': 'fa-solid fa-image',
    };
    return map[ext] || 'fa-file';
}
