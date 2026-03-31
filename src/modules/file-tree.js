/**
 * File tree and documents management module for MemoraRAG
 * 处理目录树渲染、状态加载、重新索引及文件上传预览
 */

import { state } from './store.js';
import { UI } from './ui.js';
import { API } from './api.js';
import { TRANSLATIONS } from './i18n.js';
import { getFileIcon, escapeHtml } from './utils.js';
import { mdRenderer } from './markdown.js';

export const FileTree = {
    /**
     * 加载当前系统状态（模型、索引状态、最近文档）
     */
    async loadStatus() {
        try {
            const data = await API.fetch('/api/status');
            const { status } = data;
            
            // 更新 Store
            state.status = {
                llm_model: status.llm_model,
                embed_model: status.embed_model,
                has_index: status.has_index,
                is_online: true
            };
            
            // 更新 UI
            const { valLlmModel, valEmbedModel, valIndexStatus } = UI.elements;
            if (valLlmModel) valLlmModel.textContent = status.llm_model;
            if (valEmbedModel) valEmbedModel.textContent = status.embed_model;
            
            if (valIndexStatus) {
                const dict = TRANSLATIONS[state.currentLang];
                if (status.has_index) {
                    valIndexStatus.innerHTML = `<span class="status-pill success"><i class="fa-solid fa-circle-check"></i> ${dict.status_normal}</span>`;
                } else {
                    valIndexStatus.innerHTML = `<span class="status-pill error"><i class="fa-solid fa-circle-xmark"></i> ${dict.status_not_indexed}</span>`;
                }
            }
            
            return status.memories || [];
        } catch (error) {
            console.error("加载状态失败:", error);
            const dict = TRANSLATIONS[state.currentLang];
            if (UI.elements.valIndexStatus) {
                UI.elements.valIndexStatus.innerHTML = `<span class="status-pill error"><i class="fa-solid fa-triangle-exclamation"></i> ${dict.status_load_failed}</span>`;
            }
            return [];
        }
    },

    /**
     * 加载并渲染目录树
     */
    async loadFileTree() {
        const { fileTree } = UI.elements;
        if (!fileTree) return;

        try {
            const memories = await this.loadStatus();
            const treeData = await API.fetch('/api/files');
            
            fileTree.innerHTML = '';
            const rootNode = this.renderTreeNode(treeData, true, memories);
            fileTree.appendChild(rootNode);
        } catch (error) {
            console.error("加载文件树失败:", error);
            fileTree.innerHTML = '<div class="tree-loading tree-loading-error"><i class="fa-solid fa-triangle-exclamation"></i> 目录树加载失败</div>';
        }
    },

    renderTreeNode(node, isExpanded = false, memories = []) {
        const div = document.createElement('div');
        div.className = `tree-node ${isExpanded ? 'expanded' : ''}`;
        
        const item = document.createElement('div');
        item.className = `tree-item ${node.type === 'file' ? 'is-file' : 'is-dir'}`;
        
        const icon = document.createElement('i');
        if (node.type === 'directory') {
            const chevron = document.createElement('i');
            chevron.className = 'fa-solid fa-chevron-right chevron-icon';
            item.appendChild(chevron);
            
            const isSkillDir = node.name.toLowerCase() === 'skills';
            icon.className = `fa-solid ${isSkillDir ? 'fa-star' : 'fa-folder'} tree-icon`;
            if (isSkillDir) icon.style.color = '#eab308';
        } else {
            icon.className = `fa-solid ${getFileIcon(node.name)} tree-icon`;
        }
        item.appendChild(icon);
        
        const label = document.createElement('span');
        label.className = 'tree-label';
        label.textContent = node.name;
        item.appendChild(label);

        // 记忆标记
        if (node.type === 'file' && node.path) {
            const normalizedPath = node.path.replace(/\\/g, "/").replace(/^\.?\//, "");
            if (memories.includes(encodeURIComponent(normalizedPath))) {
                const badge = document.createElement('i');
                badge.className = 'fa-solid fa-brain memory-badge';
                badge.title = 'HAS MEMORY / 有历史见解';
                item.appendChild(badge);
            }
        }
        
        if (node.type === 'file') {
            item.title = "Double click to preview / 双击预览文件";
            item.addEventListener('dblclick', (e) => {
                e.stopPropagation();
                this.openFilePreview(node.path || node.name);
            });
        }
        
        div.appendChild(item);
        
        if (node.type === 'directory' && node.children && node.children.length > 0) {
            const childrenWrapper = document.createElement('div');
            childrenWrapper.className = 'tree-children';
            node.children.forEach(child => {
                childrenWrapper.appendChild(this.renderTreeNode(child, false, memories));
            });
            div.appendChild(childrenWrapper);
            item.addEventListener('click', () => div.classList.toggle('expanded'));
        }
        return div;
    },

    /**
     * 加载建议文档 (Top Files)
     */
    async loadTopFiles() {
        const { topFilesContainer: container } = UI.elements;
        if (!container) return;
        
        try {
            const data = await API.fetch('/api/top_files');
            container.innerHTML = '';
            if (data.files && data.files.length > 0) {
                data.files.forEach(file => {
                    const btn = document.createElement('button');
                    btn.className = 'chip';
                    const basename = file.split('/').pop();
                    btn.innerHTML = `<i class="fa-solid ${getFileIcon(basename)}"></i> 分析 ${basename}`;
                    btn.onclick = () => {
                        if (state.isProcessing) return;
                        UI.elements.chatInput.value = `帮我分析一下 ${file} 文件`;
                        UI.elements.chatInput.dispatchEvent(new Event('input'));
                        UI.elements.chatInput.focus();
                        setTimeout(() => UI.elements.btnSend.click(), 50);
                    };
                    container.appendChild(btn);
                });
            } else {
                container.innerHTML = `<div class="suggestion-empty">${TRANSLATIONS[state.currentLang].welcome_subtitle}</div>`;
            }
        } catch (e) {
            console.error('Error loading top files:', e);
        }
    },

    /**
     * 重新构建索引 (SSE)
     */
    async triggerReindex(showToastUI = true) {
        if (showToastUI) {
            UI.showToast(TRANSLATIONS[state.currentLang].rebuild_index, "正在启动...", true);
        }
        
        if (UI.elements.btnReindex) UI.elements.btnReindex.disabled = true;
        if (UI.elements.indexProgressContainer) UI.elements.indexProgressContainer.style.display = 'block';

        try {
            const resp = await fetch('/api/index', { method: 'POST', headers: API.getHeaders() });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            const handleEvent = (event, data) => {
                if (!showToastUI) return;
                UI.elements.toastDesc.textContent = data;
                if (event === 'progress') {
                    const progMatch = data.match(/\((\d+)\/(\d+)\)/);
                    if (progMatch) {
                        const percent = (parseInt(progMatch[1]) / parseInt(progMatch[2])) * 100;
                        UI.elements.toastProgressBar.style.width = percent + '%';
                        UI.elements.toastProgressContainer.style.display = 'block';
                        
                        // 同步侧边栏进度条
                        if (UI.elements.indexProgressBar) UI.elements.indexProgressBar.style.width = percent + '%';
                    }
                } else if (event === 'success') {
                    if (UI.elements.indexProgressContainer) UI.elements.indexProgressContainer.style.display = 'none';
                    UI.showToast(TRANSLATIONS[state.currentLang].index_success, data, false, '<i class="fa-solid fa-check-circle" style="color:var(--success);font-size:3rem;"></i>');
                    setTimeout(() => UI.hideToast(), 2000);
                }
            };

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                buffer = API.processSseBuffer(buffer, handleEvent);
            }
            this.loadFileTree();
        } catch (e) {
            console.error("Reindex failed:", e);
        } finally {
            if (UI.elements.btnReindex) UI.elements.btnReindex.disabled = false;
            // 如果是在错误阶段结束，延时隐藏进度条
            setTimeout(() => {
                if (UI.elements.indexProgressContainer) UI.elements.indexProgressContainer.style.display = 'none';
            }, 3000);
        }
    },

    /**
     * 文件预览弹窗逻辑
     */
    async openFilePreview(path) {
        const { previewOverlay, previewFilename, previewBody } = UI.elements;
        if (!previewOverlay) return;

        try {
            UI.showToast("文件加载中", path, true);
            const data = await API.fetch(`/api/files/content?path=${encodeURIComponent(path)}`);
            UI.hideToast();

            if (data.ok) {
                previewFilename.textContent = data.filename || path;
                let contentHtml = '';
                const suffix = (data.filename || path).toLowerCase();

                if (data.is_image) {
                    contentHtml = `<div class="preview-image-container"><img src="${data.content}"></div>`;
                } else if (data.is_pdf) {
                    const pdfRes = await fetch(data.raw_url, { headers: API.getHeaders() });
                    const blobUrl = URL.createObjectURL(await pdfRes.blob());
                    contentHtml = `<iframe src="${blobUrl}" style="width:100%;height:70vh;border:none;"></iframe>`;
                    // 清理 Blob URL
                    const oldClose = UI.elements.btnClosePreview.onclick;
                    UI.elements.btnClosePreview.onclick = () => {
                        URL.revokeObjectURL(blobUrl);
                        if (oldClose) oldClose();
                        previewOverlay.style.display = 'none';
                        document.body.style.overflow = '';
                    };
                } else {
                    const isMd = suffix.endsWith('.md');
                    contentHtml = isMd ? await mdRenderer.render(data.content) : `<pre><code>${escapeHtml(data.content)}</code></pre>`;
                }

                previewBody.innerHTML = contentHtml;
                if (typeof hljs !== 'undefined') {
                    previewBody.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
                }
                previewOverlay.style.display = 'flex';
                previewOverlay.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        } catch (e) {
            UI.hideToast();
            alert("预览失败：" + e.message);
        }
    },

    /**
     * 初始化拖拽上传
     */
    initDragDrop() {
        const overlay = UI.elements.dropOverlay;
        if (!overlay) return;
        let dragCounter = 0;

        document.addEventListener('dragenter', (e) => {
            e.preventDefault();
            dragCounter++;
            overlay.classList.add('active');
        });

        document.addEventListener('dragleave', () => {
            dragCounter--;
            if (dragCounter === 0) overlay.classList.remove('active');
        });

        document.addEventListener('dragover', (e) => e.preventDefault());

        document.addEventListener('drop', async (e) => {
            e.preventDefault();
            dragCounter = 0;
            overlay.classList.remove('active');
            const items = e.dataTransfer.items;
            if (!items) return;

            const filesToUpload = [];
            const scanEntry = async (entry, path = "") => {
                if (entry.isFile) {
                    const file = await new Promise(r => entry.file(r));
                    filesToUpload.push({ file, path: path + file.name });
                } else if (entry.isDirectory) {
                    const reader = entry.createReader();
                    const subEntries = await new Promise(r => reader.readEntries(r));
                    for (const sub of subEntries) await scanEntry(sub, path + entry.name + "/");
                }
            };

            for (const item of items) {
                const entry = item.webkitGetAsEntry();
                if (entry) await scanEntry(entry);
            }

            if (filesToUpload.length > 0) {
                const dict = TRANSLATIONS[state.currentLang];
                const mode = await UI.showConfirm(dict.drop_title, `确认上传 ${filesToUpload.length} 个文件？`);
                if (mode) this.handleUpload(filesToUpload);
            }
        });
    },

    async handleUpload(filesWithPaths) {
        const formData = new FormData();
        filesWithPaths.forEach(item => {
            formData.append('files', item.file);
            formData.append('relative_paths', item.path);
        });

        UI.showToast("文件上传中", `正在上传 ${filesWithPaths.length} 个文件...`, true);
        try {
            const result = await API.fetch('/api/upload', {
                method: 'POST',
                headers: API.getHeaders(),
                body: formData
            });
            if (result.ok) {
                UI.showToast("上传成功", "文件已进入知识库，建议重新构建索引。", false);
                setTimeout(() => UI.hideToast(), 3000);
                this.loadFileTree();
            }
        } catch (e) {
            UI.showToast("上传失败", e.message, false);
        }
    }
};
