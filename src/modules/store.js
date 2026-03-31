/**
 * Lightweight Proxy-based State Machine for MemorRAG
 * 数据驱动 UI：当 state 变化时自动通知所有订阅者
 */

const initialState = {
    // 核心数据
    sessions: [],
    currentSessionId: localStorage.getItem('rag_session_id') || null,
    chatHistory: [],
    
    // 系统状态
    status: {
        llm_model: '--',
        embed_model: '--',
        has_index: false,
        is_online: true
    },
    
    // UI 状态
    currentLang: localStorage.getItem('rag_language') || 'zh',
    isProcessing: false,
    autoScrollLocked: false,
    
    // 实时日志
    logs: []
};

const subscribers = new Set();

/**
 * 订阅状态变化
 * @param {Function} callback - 状态变化时的回调函数 (state, property, value)
 */
export const subscribe = (callback) => {
    subscribers.add(callback);
    return () => subscribers.delete(callback);
};

const emit = (prop, value, receiver) => {
    subscribers.forEach(callback => callback(receiver, prop, value));
};

export const state = new Proxy(initialState, {
    set(target, prop, value, receiver) {
        // 防止冗余更新
        if (target[prop] === value && typeof value !== 'object') {
            return true;
        }
        
        target[prop] = value;
        
        // 特殊处理：持久化到 localStorage
        if (prop === 'currentSessionId') {
            if (value) localStorage.setItem('rag_session_id', value);
            else localStorage.removeItem('rag_session_id');
        }
        if (prop === 'currentLang') {
            localStorage.setItem('rag_language', value);
        }
        
        // 通知所有订阅者
        emit(prop, value, target);
        
        return true;
    }
});

// 打印状态变更日志 (开发调试用)
if (import.meta.env.DEV) {
    subscribe((s, prop, val) => {
        console.log(`[Store Update] ${prop} ->`, val);
    });
}
