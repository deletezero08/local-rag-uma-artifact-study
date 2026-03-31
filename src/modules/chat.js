/**
 * Chat and streaming interaction module for MemoraRAG
 * 处理消息渲染、SSE 流式接收及自动滚动逻辑
 */

import { state } from './store.js';
import { UI } from './ui.js';
import { API } from './api.js';
import { mdRenderer } from './markdown.js';
import { Sessions } from './sessions.js';
import { escapeHtml } from './utils.js';

export const Chat = {
    // 自动滚动控制
    AUTO_SCROLL_THRESHOLD: 40,
    isProgrammaticScroll: false,
    autoScrollLockedByUser: false,

    // 渲染节流状态
    renderTask: {
        isRendering: false,
        pendingMarkdown: '',
        targetNode: null,
        animationFrameId: null
    },

    /**
     * 初始化聊天模块
     */
    init() {
        this.addScrollListeners();
    },

    /**
     * 渲染完整会话历史
     */
    async renderChatHistory() {
        const { chatHistory, welcomeState } = UI.elements;
        if (!chatHistory) return;

        // 清空非欢迎界面元素
        Array.from(chatHistory.children).forEach(child => {
            if (child.id !== 'welcome-state' && !child.classList.contains('welcome-container')) {
                child.remove();
            }
        });

        if (state.chatHistory.length === 0) {
            welcomeState.style.display = 'flex';
            welcomeState.classList.remove('hidden');
        } else {
            welcomeState.style.display = 'none';
            welcomeState.classList.add('hidden');
            // 并行触发消息解析
            const promises = state.chatHistory.map(async pair => {
                await this.appendMessage('user', pair.user, false);
                await this.appendMessage('assistant', pair.assistant, false, pair.sources);
            });
            await Promise.all(promises);
            this.scrollToBottom(true);
        }
    },

    /**
     * 追加单条消息
     */
    async appendMessage(role, text, animate = true, sources = []) {
        const { chatHistory } = UI.elements;
        if (!chatHistory) return;
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}-message`;
        msgDiv.setAttribute('role', 'article');
        msgDiv.setAttribute('aria-label', role === 'user' ? 'You said' : 'AI AI Assistant response');
        if (animate) msgDiv.style.animation = 'fadeIn 0.3s ease';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'avatar';
        if (role === 'user') {
            avatarDiv.innerHTML = `<img src="/images/user_avatar.png" class="avatar user-avatar-img" alt="User">`;
        } else {
            avatarDiv.innerHTML = `<i class="fa-solid fa-robot"></i>`;
        }

        const contentDiv = document.createElement('div');
        contentDiv.className = 'content';
        
        if (role === 'user') {
            contentDiv.innerHTML = `<p>${escapeHtml(text)}</p>`;
        } else {
            // 异步解析 Markdown
            contentDiv.innerHTML = await mdRenderer.render(text);
            if (sources && sources.length > 0) {
                const sourceHtml = sources.map(s => `<span class="source-tag"><i class="fa-solid fa-link"></i> ${s}</span>`).join('');
                contentDiv.innerHTML += `
                    <div class="sources-box">
                        <div class="sources-title"><i class="fa-solid fa-book-open"></i> 参考来源：</div>
                        <div class="sources-list">${sourceHtml}</div>
                    </div>
                `;
            }
        }

        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(contentDiv);
        chatHistory.appendChild(msgDiv);
        
        if (animate) this.scrollToBottom();
        return contentDiv;
    },

    /**
     * 发送并处理大模型流式响应
     */
    async sendMessage() {
        const text = UI.elements.chatInput.value.trim();
        if (!text || state.isProcessing) return;

        state.isProcessing = true;
        this.autoScrollLockedByUser = false; 

        // 1. 清理输入框
        UI.elements.chatInput.value = '';
        UI.elements.chatInput.style.height = 'auto';
        UI.elements.btnSend.disabled = true;

        if (!state.currentSessionId) await Sessions.createSession();
        if (!state.currentSessionId) {
            state.isProcessing = false;
            return;
        }

        // 2. 隐藏欢迎状态
        if (UI.elements.welcomeState) UI.elements.welcomeState.style.display = 'none';

        // 3. 渲染本地用户消息
        UI.elements.chatHistory.insertAdjacentHTML('beforeend', `
            <div class="message user-message">
                <img src="/images/user_avatar.png" class="avatar user-avatar-img" alt="User">
                <div class="content"><p>${escapeHtml(text)}</p></div>
            </div>
        `);
        this.scrollToBottom(true);

        // 4. 插入 AI 等待占位符
        const thinkingId = 'msg-' + Date.now();
        UI.elements.chatHistory.insertAdjacentHTML('beforeend', `
            <div class="message ai-message" id="${thinkingId}">
                <div class="avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="content temp-content">
                    <div class="thinking-indicator">
                        <div class="thinking-spinner"></div>
                        <span class="thinking-text">深度思考中，正在检索知识库...</span>
                    </div>
                </div>
            </div>
        `);
        this.scrollToBottom(true);

        const contentNode = document.getElementById(thinkingId).querySelector('.content');

        // 5. 组装历史上下文
        const history = state.chatHistory.flatMap(pair => [
            { role: "user", content: pair.user },
            { role: "assistant", content: pair.assistant }
        ]);

        try {
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: API.getHeaders(true),
                body: JSON.stringify({ query: text, history: history })
            });
            if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let rawText = '';
            let sources = [];
            let firstToken = true;

            const handleStreamEvent = (event, data) => {
                if (event === 'token') {
                    if (firstToken) {
                        contentNode.classList.remove('temp-content');
                        contentNode.innerHTML = '';
                        firstToken = false;
                    }
                    try {
                        const payload = JSON.parse(data);
                        rawText += payload.text;
                        // 触发节流渲染
                        this.scheduleThrottledRender(rawText, contentNode);
                    } catch (e) {
                        console.error("Token parse error", e);
                    }
                } else if (event === 'status') {
                    const textNode = contentNode.querySelector('.thinking-text');
                    if (textNode) textNode.textContent = data;
                } else if (event === 'sources') {
                    try { sources = JSON.parse(data); } catch(e) {}
                }
            };

            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                buffer = API.processSseBuffer(buffer, handleStreamEvent);
            }

            // 6. 最终清理与保存
            if (sources.length > 0) {
                const sourceHtml = sources.map(s => `<span class="source-tag"><i class="fa-solid fa-link"></i> ${s}</span>`).join('');
                contentNode.innerHTML += `<div class="sources-box"><div class="sources-list">${sourceHtml}</div></div>`;
            }

            const messagePair = { user: text, assistant: rawText, sources: sources };
            state.chatHistory.push(messagePair);
            
            // 后端异步同步
            API.fetch(`/api/sessions/${state.currentSessionId}/message`, {
                method: 'POST',
                isJson: true,
                body: JSON.stringify({ message_pair: messagePair })
            });

        } catch (error) {
            contentNode.innerHTML = `<p class="chat-error-message">⚠️ 响应失败：${error.message}</p>`;
        } finally {
            state.isProcessing = false;
        }
    },

    /**
     * 节流渲染调度器
     */
    scheduleThrottledRender(mdText, domNode) {
        this.renderTask.pendingMarkdown = mdText;
        this.renderTask.targetNode = domNode;

        if (this.renderTask.isRendering) return;

        this.renderTask.isRendering = true;
        this.renderTask.animationFrameId = requestAnimationFrame(async () => {
            const textToRender = this.renderTask.pendingMarkdown;
            const target = this.renderTask.targetNode;

            // 调用 Worker 异步解析
            const html = await mdRenderer.render(textToRender);
            
            if (target) {
                target.innerHTML = html;
                this.scrollToBottom();
            }

            this.renderTask.isRendering = false;

            // 如果在解析期间又有新内容，递归下一帧
            if (this.renderTask.pendingMarkdown !== textToRender) {
                this.scheduleThrottledRender(this.renderTask.pendingMarkdown, target);
            }
        });
    },

    /**
     * 自动卷动至底部
     */
    scrollToBottom(force = false) {
        const container = UI.elements.chatHistory;
        if (!container || (!force && this.autoScrollLockedByUser)) return;

        if (force || this.isNearBottom()) {
            this.isProgrammaticScroll = true;
            container.scrollTop = container.scrollHeight;
            requestAnimationFrame(() => this.isProgrammaticScroll = false);
        }
    },

    isNearBottom() {
        const container = UI.elements.chatHistory;
        return (container.scrollHeight - container.scrollTop - container.clientHeight) <= this.AUTO_SCROLL_THRESHOLD;
    },

    addScrollListeners() {
        const container = UI.elements.chatHistory;
        if (!container) return;
        
        container.addEventListener('scroll', () => {
            if (this.isProgrammaticScroll) return;
            this.autoScrollLockedByUser = !this.isNearBottom();
        });
    }
};
