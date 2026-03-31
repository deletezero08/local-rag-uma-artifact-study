/**
 * Session management module for MemoraRAG
 * 处理会话的 CRUD 逻辑及列表渲染
 */

import { state } from './store.js';
import { UI } from './ui.js';
import { API } from './api.js';
import { TRANSLATIONS } from './i18n.js';
import { formatTimestamp } from './utils.js';

export const Sessions = {
    /**
     * 加载所有历史会话
     */
    async loadSessions() {
        try {
            const result = await API.fetch('/api/sessions');
            if (result.ok) {
                state.sessions = result.sessions;
                this.renderSessionList();
            }
        } catch (e) {
            console.error("Failed to load sessions:", e);
        }
    },

    /**
     * 渲染侧边栏会话列表
     */
    renderSessionList() {
        const { sessionList } = UI.elements;
        if (!sessionList) return;

        sessionList.innerHTML = '';
        if (state.sessions.length === 0) return;

        state.sessions.forEach(s => {
            const item = document.createElement('div');
            const isActive = state.currentSessionId === s.id;
            item.className = `session-item ${isActive ? 'active' : ''}`;
            item.setAttribute('role', 'listitem');
            item.setAttribute('aria-selected', isActive ? 'true' : 'false');
            item.onclick = (e) => {
                if (e.target.closest('.btn-delete-session')) return;
                this.switchSession(s.id);
            };

            const timeStr = formatTimestamp(s.updated_at);
            item.innerHTML = `
                <div class="session-info">
                    <div class="session-title">${s.title}</div>
                    <div class="session-time">${timeStr}</div>
                </div>
                <button class="btn-delete-session" title="Delete Chat">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            `;

            const btnDel = item.querySelector('.btn-delete-session');
            btnDel.onclick = (e) => {
                e.stopPropagation();
                this.deleteSession(s.id);
            };

            sessionList.appendChild(item);
        });
    },

    /**
     * 创建新会话
     */
    async createSession() {
        try {
            const now = new Date();
            const timeStr = now.getHours().toString().padStart(2, '0') + ":" + now.getMinutes().toString().padStart(2, '0');
            const dict = TRANSLATIONS[state.currentLang];
            const sessionTitle = state.currentLang === 'zh' ? `新会话 (${timeStr})` : `New Chat (${timeStr})`;

            const result = await API.fetch('/api/sessions', {
                method: 'POST',
                isJson: true,
                body: JSON.stringify({ title: sessionTitle })
            });

            if (result.ok) {
                state.currentSessionId = result.session_id;
                state.chatHistory = [];
                // 移动端收起侧边栏
                UI.toggleSidebar(false);
                this.loadSessions();
            }
        } catch (e) {
            console.error("Failed to create session:", e);
        }
    },

    /**
     * 切换到指定会话
     */
    async switchSession(id) {
        if (state.isProcessing) {
            UI.showToast(
                state.currentLang === 'zh' ? "已为您排队" : "Queued",
                state.currentLang === 'zh' ? `AI 正在回答，完成后将自动为您切换到会话` : `AI is responding, will switch automatically after`,
                false,
                '<i class="fa-solid fa-clock-rotate-left" style="font-size:3rem;color:var(--accent);margin-bottom:10px;"></i>'
            );
            return;
        }

        if (state.currentSessionId === id && state.chatHistory.length > 0) return;

        try {
            const result = await API.fetch(`/api/sessions/${id}`);
            if (result.ok) {
                state.currentSessionId = id;
                state.chatHistory = result.session.history || [];
                if (UI.elements.chatTitle) UI.elements.chatTitle.textContent = result.session.title;
                // 移动端收起侧边栏
                UI.toggleSidebar(false);
                this.loadSessions();
            }
        } catch (e) {
            console.error("Failed to switch session:", e);
        }
    },

    /**
     * 删除指定会话
     */
    async deleteSession(id) {
        const dict = TRANSLATIONS[state.currentLang];
        const confirmed = await UI.showConfirm(dict.confirm_delete_title, dict.chat_clear_confirm);
        if (!confirmed) return;

        try {
            const result = await API.fetch(`/api/sessions/${id}`, { method: 'DELETE' });
            if (result.ok) {
                if (state.currentSessionId === id) {
                    state.currentSessionId = null;
                    state.chatHistory = [];
                    if (UI.elements.chatTitle) UI.elements.chatTitle.textContent = dict.nav_title;
                }
                this.loadSessions();
            }
        } catch (e) {
            console.error("Failed to delete session:", e);
        }
    },

    /**
     * 保存文档心得 (会话摘要)
     */
    async saveInsights() {
        if (!state.currentSessionId || state.chatHistory.length === 0) return;

        const btn = UI.elements.btnSaveInsights;
        const originalHtml = btn.innerHTML;
        const dict = TRANSLATIONS[state.currentLang];

        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${dict.saving}`;
        btn.classList.add('processing');

        UI.showToast(
            state.currentLang === 'zh' ? "正在提炼知识记忆..." : "Distilling Insights...",
            state.currentLang === 'zh' ? "AI 正在分析本次会话的精华数据" : "AI is analyzing session key data",
            true
        );

        try {
            const result = await API.fetch(`/api/sessions/${state.currentSessionId}/summarize`, { method: 'POST' });
            if (result.ok) {
                btn.classList.remove('processing');
                btn.classList.add('success');
                btn.innerHTML = `<i class="fa-solid fa-check"></i> ${dict.saved}`;

                UI.showToast(
                    state.currentLang === 'zh' ? "记忆已存入" : "Memory Saved",
                    `${dict.memory_success} (Files: ${result.files.join(', ')})`,
                    false,
                    '<i class="fa-solid fa-check-circle" style="font-size:3rem;color:var(--success);margin-bottom:10px;"></i>'
                );

                setTimeout(() => {
                    btn.disabled = false;
                    btn.innerHTML = originalHtml;
                    btn.classList.remove('success');
                    UI.hideToast();
                }, 2000);
                
                return true; // 返回成功，以便外部刷新文件树
            }
        } catch (e) {
            console.error("Failed to save insights:", e);
            btn.disabled = false;
            btn.innerHTML = originalHtml;
            btn.classList.remove('processing');
            UI.showToast("Error", e.message || dict.memory_error, false);
            setTimeout(() => UI.hideToast(), 3000);
        }
        return false;
    }
};
