/**
 * Markdown 异步渲染桥接模块
 * 封装与 Web Worker 的通信逻辑，提供 Promise 接口
 */

import MarkdownWorker from '../workers/markdown.worker.js?worker';

class MarkdownRenderer {
    constructor() {
        this.worker = new MarkdownWorker();
        this.messageQueue = new Map(); // 并发解析 ID 映射
        this.msgIdCounter = 0;

        // 监听子线程返回的结果
        this.worker.onmessage = (e) => {
            const { id, html, error } = e.data;
            if (this.messageQueue.has(id)) {
                const resolve = this.messageQueue.get(id);
                resolve(html);
                this.messageQueue.delete(id);
            }
        };

        this.worker.onerror = (e) => {
            console.error('[MarkdownWorker] Critical Error:', e);
        };
    }

    /**
     * 暴露给外部的异步解析接口
     * @param {string} markdownText 
     * @returns {Promise<string>}
     */
    async render(markdownText) {
        if (!markdownText) return '';
        return new Promise((resolve) => {
            const id = this.msgIdCounter++;
            this.messageQueue.set(id, resolve);
            this.worker.postMessage({ id, text: markdownText });
        });
    }
}

// 导出单例，确保全站共享一个渲染 Worker 线程池（单线程）
export const mdRenderer = new MarkdownRenderer();
