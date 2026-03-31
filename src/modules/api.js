/**
 * API communication module for MemoraRAG
 * 封装所有 fetch 请求和 SSE 解析
 */

const API_KEY = ""; // Optional override; by default auth is handled by HttpOnly cookie.

export const API = {
    /**
     * 获取通用的请求头
     * @param {boolean} isJson - 是否发送 JSON
     */
    getHeaders(isJson = false) {
        const headers = {};
        if (API_KEY) {
            headers["Authorization"] = `Bearer ${API_KEY}`;
        }
        if (isJson) {
            headers["Content-Type"] = "application/json";
        }
        return headers;
    },

    /**
     * 通用 Fetch 包装
     */
    async fetch(url, options = {}) {
        const headers = { ...this.getHeaders(options.isJson), ...options.headers };
        const resp = await fetch(url, {
            ...options,
            headers
        });
        if (!resp.ok) {
            const errorData = await resp.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${resp.status}`);
        }
        return resp.json();
    },

    /**
     * 处理 SSE 流数据缓冲区
     * @param {string} buffer - 未处理完的文本块
     * @param {Function} onEvent - (event, data) 回调
     */
    processSseBuffer(buffer, onEvent) {
        let normalized = buffer.replace(/\r\n/g, '\n');
        let boundary = normalized.indexOf('\n\n');

        while (boundary !== -1) {
            const eventStr = normalized.slice(0, boundary);
            normalized = normalized.slice(boundary + 2);
            boundary = normalized.indexOf('\n\n');

            if (!eventStr.trim()) continue;

            const lines = eventStr.split('\n');
            let currentEvent = null;
            let currentData = '';

            for (const line of lines) {
                if (line.startsWith('event:')) {
                    currentEvent = line.replace('event:', '').trim();
                } else if (line.startsWith('data:')) {
                    currentData += line.slice(5).trimStart();
                }
            }
            onEvent(currentEvent, currentData);
        }
        return normalized;
    }
};
