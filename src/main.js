/**
 * MemoraRAG Main Entry Point (Orchestrator)
 * 职责：初始化模块、注入依赖、全局事件管理
 */

import { state, subscribe } from './modules/store.js';
import { UI } from './modules/ui.js';
import { API } from './modules/api.js';
import { I18n } from './modules/i18n.js';
import { Sessions } from './modules/sessions.js';
import { FileTree } from './modules/file-tree.js';
import { Chat } from './modules/chat.js';

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[MemoraRAG] Initializing system...');

    // 1. 初始化核心模块 (基础)
    UI.init();
    
    // 2. 初始化核心业务
    await I18n.init(state.currentLang);
    await Sessions.loadSessions();
    await FileTree.loadFileTree();
    await FileTree.loadTopFiles();
    Chat.init();

    // 3. 全局事件绑定 (非模块私有的)
    bindGlobalListeners();

    // 4. 状态订阅 (数据驱动 UI)
    bindStoreSubscriptions();

    console.log('[MemoraRAG] System online.');
});

/**
 * 集中管理全局 DOM 事件触发逻辑
 */
function bindGlobalListeners() {
    const { elements } = UI;

    // 语言切换
    elements.btnLangToggle?.addEventListener('click', () => {
        const nextLang = state.currentLang === 'zh' ? 'en' : 'zh';
        I18n.setLanguage(nextLang);
    });

    // 新建会话
    elements.btnNewChat?.addEventListener('click', () => Sessions.createSession());

    // 保存见解
    elements.btnSaveInsights?.addEventListener('click', async () => {
        const success = await Sessions.saveInsights();
        if (success) FileTree.loadFileTree(); // 如果保存了记忆，刷新树以显示大脑图标
    });

    // 重新索引
    elements.btnReindex?.addEventListener('click', () => FileTree.triggerReindex(true));

    // 发送消息
    elements.btnSend?.addEventListener('click', () => Chat.sendMessage());
    
    // 清空会话
    elements.btnClearChat?.addEventListener('click', () => {
        if (state.currentSessionId) Sessions.deleteSession(state.currentSessionId);
    });

    // 回车键盘监听
    elements.chatInput?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!elements.btnSend.disabled) Chat.sendMessage();
        }
    });

    // 输入框自适应高度
    elements.chatInput?.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        elements.btnSend.disabled = (!this.value.trim() || state.isProcessing);
    });

    // 初始化文件拖拽
    FileTree.initDragDrop();
}

/**
 * 订阅 Store 状态变化，触发响应式更新
 */
function bindStoreSubscriptions() {
    // 订阅会话列表变化 -> 刷新侧边栏
    subscribe((curr, prop) => {
        if (prop === 'sessions' || prop === 'currentSessionId') {
            Sessions.renderSessionList();
        }
    });

    // 订阅聊天历史 -> 刷新聊天主区
    subscribe((curr, prop) => {
        if (prop === 'chatHistory' || prop === 'currentSessionId') {
            Chat.renderChatHistory();
            
            // 动态更新页面标题
            const currentSession = state.sessions.find(s => s.id === state.currentSessionId);
            if (currentSession) {
                document.title = `${currentSession.title} | MemoraRAG`;
            } else {
                document.title = '忆联检索 MemoraRAG | AI 知识库';
            }
        }
    });

    // 订阅处理状态 -> 锁定/解锁 发送按钮
    subscribe((curr, prop, val) => {
        if (prop === 'isProcessing') {
            UI.elements.btnSend.disabled = val;
            UI.elements.chatInput.disabled = val;
        }
    });
}
