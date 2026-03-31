/**
 * UI Management module for MemoraRAG
 * 管理 DOM 映射、全局组件（Toast, Confirm）及基础交互（Resizing）
 */

import { state } from './store.js';

export const UI = {
    // DOM 元素映射
    elements: {},

    /**
     * 初始化 UI 模块
     */
    init() {
        this.cacheElements();
        this.initResizers();
        this.initMobileMenu();
    },

    /**
     * 缓存所有需要操作的 DOM 元素
     */
    cacheElements() {
        this.elements = {
            valLlmModel: document.getElementById('val-llm-model'),
            valEmbedModel: document.getElementById('val-embed-model'),
            valIndexStatus: document.getElementById('val-index-status'),
            fileTree: document.getElementById('file-tree'),
            btnReindex: document.getElementById('btn-rebuild-index'),
            chatInput: document.getElementById('chat-input'),
            btnSend: document.getElementById('btn-send'),
            btnClearChat: document.getElementById('btn-clear-chat'),
            chatHistory: document.getElementById('chat-history'),
            welcomeState: document.getElementById('welcome-state'),
            topFilesContainer: document.getElementById('dynamic-suggestions'),
            indexProgressContainer: document.getElementById('index-progress-container'),
            indexProgressBar: document.getElementById('index-progress-bar'),
            btnLangToggle: document.getElementById('btn-lang-toggle'),
            btnNewChat: document.getElementById('btn-new-chat'),
            sessionList: document.getElementById('session-list'),
            btnSaveInsights: document.getElementById('btn-save-insights'),
            chatTitle: document.getElementById('current-chat-title'),
            
            // Confirm Modal
            confirmOverlay: document.getElementById('confirm-overlay'),
            confirmTitle: document.getElementById('confirm-title'),
            confirmDesc: document.getElementById('confirm-desc'),
            confirmIcon: document.getElementById('confirm-icon'),
            confirmButtons: document.getElementById('confirm-buttons'),
            
            // Sidebar Resize
            sidebar: document.querySelector('.sidebar'),
            sidebarHandle: document.getElementById('sidebar-resize-handle'),
            appContainer: document.querySelector('.app-container'),

            // Toast / Progress
            toastOverlay: document.getElementById('toast-overlay'),
            spinner: document.querySelector('.spinner'),
            toastTitle: document.getElementById('toast-title'),
            toastDesc: document.getElementById('toast-desc'),
            toastProgressContainer: document.querySelector('.progress-bar-container'),
            toastProgressBar: document.getElementById('toast-progress-bar'),

            // Logs
            logDrawer: document.getElementById('log-drawer'),
            btnToggleLogs: document.getElementById('btn-toggle-logs'),
            btnCloseLogs: document.getElementById('btn-close-logs'),
            btnClearLogs: document.getElementById('btn-clear-logs'),
            logContainer: document.getElementById('log-container'),
            logResizeHandle: document.getElementById('log-resize-handle'),
            dropOverlay: document.getElementById('drop-overlay'),
            
            // Preview
            previewOverlay: document.getElementById('preview-overlay'),
            previewFilename: document.getElementById('preview-filename'),
            previewBody: document.getElementById('preview-body'),
            btnClosePreview: document.getElementById('btn-close-preview'),

            // Mobile Menu
            btnMobileMenu: document.getElementById('btn-mobile-menu'),
            sidebarOverlay: document.getElementById('sidebar-overlay'),
        };
    },

    /**
     * 初始化调整大小的手柄
     */
    initResizers() {
        this.initSidebarResize();
        this.initLogResizer();
    },

    initSidebarResize() {
        const { sidebarHandle: handle, sidebar, appContainer: container } = this.elements;
        if (!handle || !sidebar) return;

        let isResizing = false;
        const savedWidth = localStorage.getItem('sidebar_width');
        if (savedWidth) sidebar.style.width = savedWidth + 'px';

        handle.addEventListener('mousedown', () => {
            isResizing = true;
            handle.classList.add('active');
            container.classList.add('resizing-sidebar');
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            let newWidth = e.clientX - sidebar.getBoundingClientRect().left;
            newWidth = Math.max(200, Math.min(600, newWidth));
            sidebar.style.width = newWidth + 'px';
            localStorage.setItem('sidebar_width', newWidth);
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                handle.classList.remove('active');
                container.classList.remove('resizing-sidebar');
            }
        });
    },

    initLogResizer() {
        const { logResizeHandle: handle, logDrawer: drawer } = this.elements;
        if (!handle) return;

        let isResizing = false;
        handle.addEventListener('mousedown', (e) => {
            isResizing = true;
            drawer.classList.add('resizing');
            document.body.style.cursor = 'ns-resize';
            e.preventDefault();
        });

        window.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const newHeight = window.innerHeight - e.clientY;
            if (newHeight > 100 && newHeight < window.innerHeight * 0.8) {
                drawer.style.height = `${newHeight}px`;
                if (!drawer.classList.contains('active')) {
                    drawer.style.bottom = `-${newHeight}px`;
                }
            }
        });

        window.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                drawer.classList.remove('resizing');
                document.body.style.cursor = '';
                if (drawer.classList.contains('active')) drawer.style.bottom = '0';
            }
        });
    },

    /**
     * 显示全局 Toast 提示
     */
    showToast(title, desc, showSpinner = true, iconHtml = null) {
        const { toastOverlay, toastTitle, toastDesc, spinner, toastProgressContainer } = this.elements;
        if (!toastOverlay) return;
        
        toastTitle.innerHTML = title;
        toastDesc.textContent = desc;
        spinner.style.display = showSpinner ? 'block' : 'none';
        toastProgressContainer.style.display = 'none';
        
        const existingIcon = toastOverlay.querySelector('.toast-custom-icon');
        if (existingIcon) existingIcon.remove();
        if (iconHtml) {
            toastTitle.insertAdjacentHTML('beforebegin', `<div class="toast-custom-icon">${iconHtml}</div>`);
        }
        toastOverlay.classList.add('active');
    },

    hideToast() {
        if (this.elements.toastOverlay) {
            this.elements.toastOverlay.classList.remove('active');
        }
    },

    /**
     * 显示自定义确认弹窗
     */
    showConfirm(titleText, descText, buttons = null, iconHtml = null) {
        return new Promise((resolve) => {
            const { confirmOverlay, confirmTitle, confirmDesc, confirmIcon, confirmButtons } = this.elements;
            if (!confirmOverlay) return resolve(confirm(descText));

            confirmTitle.textContent = titleText;
            confirmDesc.textContent = descText;
            confirmIcon.innerHTML = iconHtml || `<i class="fa-solid fa-circle-question" style="color:var(--primary);font-size:2.5rem;margin-bottom:1rem;"></i>`;

            confirmButtons.innerHTML = '';
            const actionButtons = buttons || [
                { text: state.currentLang === 'zh' ? '取消' : 'Cancel', class: 'btn-action-outline', value: false },
                { text: state.currentLang === 'zh' ? '确定' : 'Confirm', class: 'btn-action-outline danger', value: true }
            ];

            actionButtons.forEach(btnCfg => {
                const btn = document.createElement('button');
                btn.textContent = btnCfg.text;
                btn.className = btnCfg.class;
                btn.onclick = () => {
                    confirmOverlay.classList.remove('active');
                    resolve(btnCfg.value);
                };
                confirmButtons.appendChild(btn);
            });

            confirmOverlay.classList.add('active');
        });
    },

    /**
     * 移动端侧边栏逻辑
     */
    initMobileMenu() {
        const { btnMobileMenu, sidebarOverlay, sidebar } = this.elements;
        if (!btnMobileMenu || !sidebarOverlay) return;

        btnMobileMenu.addEventListener('click', () => this.toggleSidebar(true));
        sidebarOverlay.addEventListener('click', () => this.toggleSidebar(false));
    },

    /**
     * 切换侧边栏显示状态 (主要用于移动端)
     * @param {boolean} forceState 
     */
    toggleSidebar(forceState) {
        const { sidebar, sidebarOverlay } = this.elements;
        if (!sidebar || !sidebarOverlay) return;

        const isActive = typeof forceState === 'boolean' ? forceState : !sidebar.classList.contains('active');
        
        if (isActive) {
            sidebar.classList.add('active');
            sidebarOverlay.classList.add('active');
            document.body.style.overflow = 'hidden'; // 防止背景滚动
        } else {
            sidebar.classList.remove('active');
            sidebarOverlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
};
