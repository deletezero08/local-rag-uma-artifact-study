/**
 * i18n Translation module for MemoraRAG
 * 管理语言包和 DOM 翻译同步
 */

import { state } from './store.js';
import { UI } from './ui.js';
import { API } from './api.js';

export const TRANSLATIONS = {
    zh: {
        nav_title: "忆联检索 MemoraRAG",
        llm_model_label: "LLM 模型",
        embed_model_label: "向量模型",
        index_status_label: "索引状态",
        knowledge_base: "知识库文档",
        rebuild_index: "重新构建索引",
        system_online: "已连接本地引擎",
        welcome_title: "今天想了解关于文档的什么？",
        welcome_subtitle: "请在左侧\"重新构建索引\"后，点击下方建议或直接输入提问。",
        loading_directory: "加载目录结构中...",
        loading_suggestions: "加载热门文档...",
        progress_starting: "即将开始...",
        input_placeholder: "向知识库提问 (Shift + Enter 换行)...",
        chat_clear_confirm: "确定清空会话吗？",
        index_building: "正在构建索引",
        index_waiting: "请稍候，由于文档较多可能需要几分钟时间...",
        index_success: "索引构建成功！",
        index_error: "索引构建失败",
        lang_toggle_btn: "EN",
        new_chat: "开启新对话",
        save_insights: "保存本文档分析心得",
        save_insights_btn: "存为记忆",
        memory_success: "知识记忆已存入大脑",
        memory_error: "提炼失败：未发现具体文件引用",
        status_online: "在线",
        status_offline: "离线",
        status_ready: "就绪",
        status_not_ready: "未就绪",
        status_persisted: "已落盘",
        status_not_persisted: "未落盘",
        status_loaded: "已加载",
        status_not_loaded: "未加载",
        status_available: "可用",
        status_not_available: "不可用",
        status_normal: "正常",
        status_not_indexed: "未构建",
        status_load_failed: "加载失败",
        saving: "正在保存...",
        saved: "已保存！",
        drop_title: "释放开始上传",
        drop_subtitle: "支持文件及文件夹批量拖入",
        uploading_title: "正在上传文件",
        upload_success: "上传成功！",
        confirm_delete_title: "确认删除会话",
        confirm_cancel: "取消",
        confirm_ok: "确定",
    },
    en: {
        nav_title: "MemoraRAG",
        llm_model_label: "LLM Model",
        embed_model_label: "Embed Model",
        index_status_label: "Index Status",
        knowledge_base: "Knowledge Base",
        rebuild_index: "Rebuild Index",
        system_online: "Local Engine Online",
        welcome_title: "What would you like to know today?",
        welcome_subtitle: "Please click a suggestion below or type your question directly.",
        loading_directory: "Loading directories...",
        loading_suggestions: "Loading popular docs...",
        progress_starting: "Starting...",
        input_placeholder: "Ask the knowledge base (Shift+Enter for newline)...",
        chat_clear_confirm: "Are you sure you want to clear the chat?",
        index_building: "Indexing...",
        index_waiting: "Please wait, this may take a few minutes for many documents...",
        index_success: "Indexing success!",
        index_error: "Indexing failed",
        lang_toggle_btn: "中",
        new_chat: "New Chat",
        save_insights: "Save Document Insights",
        save_insights_btn: "Save Memory",
        memory_success: "Insights saved to Memory",
        memory_error: "Fail: No specific file identified",
        status_online: "Online",
        status_offline: "Offline",
        status_ready: "Ready",
        status_not_ready: "Not Ready",
        status_persisted: "Saved",
        status_not_persisted: "Not Saved",
        status_loaded: "Loaded",
        status_not_loaded: "Not Loaded",
        status_available: "Available",
        status_not_available: "Not Available",
        status_normal: "Active",
        status_not_indexed: "Empty",
        status_load_failed: "Error",
        saving: "Saving...",
        saved: "Saved!",
        drop_title: "Drop to Upload",
        drop_subtitle: "Supports files and folders",
        uploading_title: "Uploading Files",
        upload_success: "Upload Success!",
        confirm_delete_title: "Confirm Deletion",
        confirm_cancel: "Cancel",
        confirm_ok: "Confirm",
    }
};

export const I18n = {
    /**
     * 初始化：根据 store 里的语言同步 UI
     */
    async init(lang) {
        await this.setLanguage(lang || state.currentLang);
    },

    /**
     * 切换语言并同步后端模型
     */
    async setLanguage(lang) {
        state.currentLang = lang;
        const dict = TRANSLATIONS[lang];
        const { elements } = UI;

        // 1. 批量更新带有 data-i18n 的元素
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (dict[key]) el.textContent = dict[key];
        });

        // 2. 更新带有 data-i18n-title 的元素
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            if (dict[key]) el.title = dict[key];
        });

        // 3. 更新特殊组件的文本
        if (elements.chatInput) elements.chatInput.placeholder = dict.input_placeholder;
        if (elements.btnLangToggle) elements.btnLangToggle.textContent = dict.lang_toggle_btn;

        // 4. 通知后端切换模型 (仅在必要时触发提示)
        try {
            const result = await API.fetch('/api/config/switch_lang', {
                method: 'POST',
                isJson: true,
                body: JSON.stringify({ lang: lang })
            });

            if (result.ok && result.changed) {
                UI.showToast(
                    lang === 'zh' ? "正在优化中文向量引擎" : "Optimizing English Engine",
                    dict.index_waiting || result.message,
                    true
                );
                setTimeout(() => UI.hideToast(), 4000);
            }
        } catch (e) {
            console.error("Autonomous model switch failed:", e);
        }
    }
};
