/**
 * Markdown Worker for MemoraRAG
 * 负责在子线程进行 Markdown 解析、HTML 过滤与语法高亮
 */

import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';

// 初始化 Marked 配置
marked.setOptions({
    highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
});

// Worker 消息监听
self.onmessage = (e) => {
    const { id, text } = e.data;
    if (!text) {
        self.postMessage({ id, html: '' });
        return;
    }

    try {
        const rawHtml = marked.parse(text);
        // Worker 中没有 window，需要使用 DOMPurify 的特殊初始化方式（Vite/Worker 环境）
        // 如果是纯字符串解析，DOMPurify 通常需要一个 DOM 实现（如 jsdom），
        // 但在现代浏览器 Worker 中，我们通常只做基础过滤或回传主线程过滤。
        // 为了极致性能，我们在 Worker 做解析，回主线程做最终 Sanitization (或者使用 Worker 兼容版)
        
        // 实际上，DOMPurify 在 Worker 环境下可以直接运行（如果环境支持）
        const safeHtml = DOMPurify.sanitize(rawHtml);
        
        self.postMessage({ id, html: safeHtml });
    } catch (err) {
        self.postMessage({ id, html: `<p style="color:red;">Render Error: ${err.message}</p>`, error: true });
    }
};
