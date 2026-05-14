// ==UserScript==
// @name         学习通 AI 智能助手
// @namespace    https://github.com/mlgmd10
// @version      2.1.0
// @description  为学习通网页版注入 AI 浮窗助手，支持智能问答、作业辅助、课程总结
// @author       GEO System
// @match        *://*.chaoxing.com/*
// @match        *://*.xuexitong.com/*
// @match        *://mooc1.chaoxing.com/*
// @match        *://i.chaoxing.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_addStyle
// @connect      api.openai.com
// @connect      api.deepseek.com
// @connect      api.moonshot.cn
// @connect      open.bigmodel.cn
// @run-at       document-end
// ==/UserScript==

(function () {
    'use strict';

    // ========== 配置区 ==========
    const CONFIG = {
        // 切换模型: 'deepseek' | 'openai' | 'moonshot' | 'glm'
        provider: GM_getValue('ai_provider', 'deepseek'),
        apiKey: GM_getValue('ai_api_key', ''),
        model: 'deepseek-chat',
        maxTokens: 2000,
        temperature: 0.7,

        // 功能开关
        enableFloatPanel: true,
        enableAutoAnswer: true,
        enableSummary: true,
        enableTranslate: true,

        // UI 配置
        panelWidth: 380,
        panelHeight: 520,
        shortcutKey: 'Alt+Q',
    };

    const API_ENDPOINTS = {
        deepseek: 'https://api.deepseek.com/v1/chat/completions',
        openai: 'https://api.openai.com/v1/chat/completions',
        moonshot: 'https://api.moonshot.cn/v1/chat/completions',
        glm: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    };

    // ========== 系统提示词 ==========
    const SYSTEM_PROMPTS = {
        default: '你是一个智能学习助手，帮助用户解答学习问题。回答要简洁、准确、有结构。',
        homework: '你是一个作业辅导专家。用户会提供题目，你需要：1)给出正确答案 2)简要解释解题思路 3)如果涉及计算，列出步骤。回答要精简，适合在聊天窗口查看。',
        summary: '你是一个课程内容总结专家。请用中文总结以下课程内容，提取核心知识点(3-5个)、关键概念和重要结论。使用分点格式输出，不超过500字。',
        translate: '你是一个翻译助手。请将以下内容翻译为目标语言，保持原意准确，语言流畅自然。',
        explain: '你是一个知识讲解专家。用通俗易懂的方式解释概念，可以使用类比、例子帮助理解。',
    };

    // ========== 状态管理 ==========
    let chatHistory = [];
    let isPanelVisible = false;
    let panelContainer = null;

    // ========== AI 调用 ==========
    async function callAI(messages, options = {}) {
        const apiKey = CONFIG.apiKey || GM_getValue('ai_api_key', '');
        if (!apiKey) {
            return { error: '请先设置 API Key (点击面板设置按钮)' };
        }

        const provider = CONFIG.provider;
        const endpoint = API_ENDPOINTS[provider];
        const modelMap = {
            deepseek: 'deepseek-chat',
            openai: 'gpt-3.5-turbo',
            moonshot: 'moonshot-v1-8k',
            glm: 'glm-4-flash',
        };

        const body = JSON.stringify({
            model: options.model || modelMap[provider] || CONFIG.model,
            messages: messages,
            max_tokens: options.maxTokens || CONFIG.maxTokens,
            temperature: options.temperature ?? CONFIG.temperature,
            stream: false,
        });

        return new Promise((resolve) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: endpoint,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`,
                },
                data: body,
                onload: (resp) => {
                    try {
                        const data = JSON.parse(resp.responseText);
                        if (data.choices && data.choices[0]) {
                            resolve({ content: data.choices[0].message.content });
                        } else if (data.error) {
                            resolve({ error: data.error.message || 'API 调用失败' });
                        } else {
                            resolve({ error: '未知响应格式' });
                        }
                    } catch (e) {
                        resolve({ error: '响应解析失败: ' + e.message });
                    }
                },
                onerror: (e) => {
                    resolve({ error: '网络请求失败，请检查 API Key 和网络' });
                },
                ontimeout: () => {
                    resolve({ error: '请求超时' });
                },
                timeout: 30000,
            });
        });
    }

    // ========== UI 组件 ==========
    GM_addStyle(`
        .xtai-panel {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: ${CONFIG.panelWidth}px;
            height: ${CONFIG.panelHeight}px;
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.18);
            display: flex;
            flex-direction: column;
            z-index: 99999;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 14px;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        .xtai-panel.minimized {
            height: 48px;
            width: 200px;
        }
        .xtai-panel.hidden {
            display: none;
        }
        .xtai-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: move;
            user-select: none;
            font-weight: 600;
            font-size: 15px;
            flex-shrink: 0;
        }
        .xtai-header-btns {
            display: flex;
            gap: 6px;
        }
        .xtai-header-btns button {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            border-radius: 4px;
            padding: 3px 8px;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.2s;
        }
        .xtai-header-btns button:hover {
            background: rgba(255,255,255,0.35);
        }
        .xtai-body {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
            background: #f8f9fa;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .xtai-msg {
            padding: 8px 12px;
            border-radius: 10px;
            max-width: 85%;
            line-height: 1.5;
            word-break: break-word;
        }
        .xtai-msg.user {
            background: #667eea;
            color: white;
            align-self: flex-end;
        }
        .xtai-msg.ai {
            background: white;
            color: #333;
            align-self: flex-start;
            border: 1px solid #e0e0e0;
        }
        .xtai-msg.error {
            background: #fff3f3;
            color: #c0392b;
            border: 1px solid #f5c6cb;
        }
        .xtai-msg.loading::after {
            content: '';
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #ccc;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: xtai-spin 0.6s linear infinite;
            margin-left: 6px;
            vertical-align: middle;
        }
        @keyframes xtai-spin {
            to { transform: rotate(360deg); }
        }
        .xtai-input-area {
            padding: 10px 12px;
            border-top: 1px solid #eee;
            display: flex;
            gap: 8px;
            background: white;
            flex-shrink: 0;
        }
        .xtai-input-area textarea {
            flex: 1;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 8px 10px;
            resize: none;
            font-size: 13px;
            font-family: inherit;
            outline: none;
            height: 38px;
            max-height: 100px;
            transition: border 0.2s;
        }
        .xtai-input-area textarea:focus {
            border-color: #667eea;
        }
        .xtai-input-area button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 14px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            transition: opacity 0.2s;
            white-space: nowrap;
        }
        .xtai-input-area button:hover {
            opacity: 0.9;
        }
        .xtai-quick-btns {
            display: flex;
            gap: 6px;
            padding: 0 12px 8px;
            flex-wrap: wrap;
        }
        .xtai-quick-btns button {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 16px;
            padding: 4px 12px;
            cursor: pointer;
            font-size: 12px;
            color: #555;
            transition: all 0.2s;
        }
        .xtai-quick-btns button:hover {
            border-color: #667eea;
            color: #667eea;
            background: #f0f0ff;
        }
        .xtai-settings {
            padding: 16px;
            background: white;
            flex: 1;
            overflow-y: auto;
        }
        .xtai-settings label {
            display: block;
            margin-bottom: 10px;
            font-size: 13px;
            color: #555;
        }
        .xtai-settings select, .xtai-settings input {
            width: 100%;
            padding: 6px 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            margin-top: 4px;
        }
        .xtai-settings .save-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            margin-top: 12px;
        }
        .xtai-float-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            z-index: 99998;
            box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
            transition: transform 0.3s;
        }
        .xtai-float-btn:hover {
            transform: scale(1.1);
        }
        .xtai-selected-text-toolbar {
            position: absolute;
            background: #333;
            color: white;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
            cursor: pointer;
            z-index: 99999;
            display: none;
            white-space: nowrap;
        }
        .xtai-selected-text-toolbar:hover {
            background: #667eea;
        }
        .xtai-toast {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #333;
            color: white;
            padding: 10px 24px;
            border-radius: 8px;
            z-index: 100000;
            font-size: 14px;
            animation: xtai-fade-in 0.3s;
        }
        @keyframes xtai-fade-in {
            from { opacity: 0; transform: translateX(-50%) translateY(-10px); }
            to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
    `);

    // ========== 面板构建 ==========
    function createPanel() {
        panelContainer = document.createElement('div');
        panelContainer.className = 'xtai-panel';
        panelContainer.innerHTML = `
            <div class="xtai-header" id="xtai-drag-handle">
                <span>🤖 AI 学习助手</span>
                <div class="xtai-header-btns">
                    <button id="xtai-clear">清空</button>
                    <button id="xtai-settings-btn">⚙</button>
                    <button id="xtai-minimize">−</button>
                    <button id="xtai-close">✕</button>
                </div>
            </div>
            <div class="xtai-quick-btns" id="xtai-quick-btns">
                <button data-action="homework">📝 作业助手</button>
                <button data-action="summary">📋 课程总结</button>
                <button data-action="explain">💡 概念讲解</button>
                <button data-action="translate">🌐 翻译</button>
            </div>
            <div class="xtai-body" id="xtai-body">
                <div class="xtai-msg ai">你好！我是 AI 学习助手，可以帮你解答问题、辅助作业、总结课程内容。请先点击 ⚙ 设置 API Key。</div>
            </div>
            <div class="xtai-input-area">
                <textarea id="xtai-input" placeholder="输入你的问题..." rows="1"></textarea>
                <button id="xtai-send">发送</button>
            </div>
            <div class="xtai-settings" id="xtai-settings-panel" style="display:none;">
                <h4 style="margin:0 0 12px;color:#333;">⚙ 设置</h4>
                <label>模型提供商
                    <select id="xtai-provider-select">
                        <option value="deepseek">DeepSeek (推荐/免费)</option>
                        <option value="moonshot">Moonshot (Kimi)</option>
                        <option value="openai">OpenAI (GPT)</option>
                        <option value="glm">智谱 GLM</option>
                    </select>
                </label>
                <label>API Key
                    <input type="password" id="xtai-apikey-input" placeholder="sk-..." />
                </label>
                <p style="font-size:11px;color:#999;margin:4px 0;">
                    获取 API Key: deepseek.com | moonshot.cn | platform.openai.com | open.bigmodel.cn
                </p>
                <button class="save-btn" id="xtai-save-settings">保存设置</button>
                <button style="margin-left:8px;background:#eee;border:none;border-radius:6px;padding:8px 16px;cursor:pointer;font-size:13px;" id="xtai-back-from-settings">返回</button>
            </div>
        `;
        document.body.appendChild(panelContainer);

        bindPanelEvents();
        loadSettings();
    }

    function bindPanelEvents() {
        const input = document.getElementById('xtai-input');
        const sendBtn = document.getElementById('xtai-send');
        const body = document.getElementById('xtai-body');
        const settingsPanel = document.getElementById('xtai-settings-panel');
        const quickBtns = document.getElementById('xtai-quick-btns');

        sendBtn.addEventListener('click', () => sendMessage());
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        document.getElementById('xtai-close').addEventListener('click', () => {
            panelContainer.classList.add('hidden');
            createFloatButton();
        });

        document.getElementById('xtai-minimize').addEventListener('click', () => {
            panelContainer.classList.toggle('minimized');
        });

        document.getElementById('xtai-clear').addEventListener('click', () => {
            chatHistory = [];
            body.innerHTML = '';
            addMessage('ai', '对话已清空，有什么可以帮助你的？');
        });

        document.getElementById('xtai-settings-btn').addEventListener('click', () => {
            body.style.display = 'none';
            quickBtns.style.display = 'none';
            settingsPanel.style.display = 'block';
            document.getElementById('xtai-provider-select').value = CONFIG.provider;
            document.getElementById('xtai-apikey-input').value = CONFIG.apiKey;
        });

        document.getElementById('xtai-back-from-settings').addEventListener('click', () => {
            body.style.display = '';
            quickBtns.style.display = '';
            settingsPanel.style.display = 'none';
        });

        document.getElementById('xtai-save-settings').addEventListener('click', () => {
            const provider = document.getElementById('xtai-provider-select').value;
            const apiKey = document.getElementById('xtai-apikey-input').value.trim();
            CONFIG.provider = provider;
            CONFIG.apiKey = apiKey;
            GM_setValue('ai_provider', provider);
            GM_setValue('ai_api_key', apiKey);
            showToast('设置已保存！');
            body.style.display = '';
            quickBtns.style.display = '';
            settingsPanel.style.display = 'none';
        });

        quickBtns.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON') {
                const action = e.target.dataset.action;
                handleQuickAction(action);
            }
        });

        // 拖拽
        let isDragging = false, offsetX, offsetY;
        const header = document.getElementById('xtai-drag-handle');
        header.addEventListener('mousedown', (e) => {
            isDragging = true;
            offsetX = e.clientX - panelContainer.getBoundingClientRect().left;
            offsetY = e.clientY - panelContainer.getBoundingClientRect().top;
        });
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            panelContainer.style.right = 'auto';
            panelContainer.style.bottom = 'auto';
            panelContainer.style.left = (e.clientX - offsetX) + 'px';
            panelContainer.style.top = (e.clientY - offsetY) + 'px';
        });
        document.addEventListener('mouseup', () => { isDragging = false; });
    }

    function createFloatButton() {
        if (document.querySelector('.xtai-float-btn')) return;
        const btn = document.createElement('button');
        btn.className = 'xtai-float-btn';
        btn.innerHTML = '🤖';
        btn.title = 'AI 学习助手 (Alt+Q)';
        btn.addEventListener('click', () => {
            panelContainer.classList.remove('hidden');
            btn.remove();
        });
        document.body.appendChild(btn);
    }

    function addMessage(role, content) {
        const body = document.getElementById('xtai-body');
        if (!body) return;
        const div = document.createElement('div');
        div.className = `xtai-msg ${role}`;
        div.textContent = content;
        body.appendChild(div);
        body.scrollTop = body.scrollHeight;
        return div;
    }

    function showToast(msg) {
        const toast = document.createElement('div');
        toast.className = 'xtai-toast';
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2000);
    }

    // ========== 消息处理 ==========
    async function sendMessage() {
        const input = document.getElementById('xtai-input');
        const msg = input.value.trim();
        if (!msg) return;

        input.value = '';
        addMessage('user', msg);
        chatHistory.push({ role: 'user', content: msg });

        const loadingDiv = addMessage('ai', '思考中...');
        loadingDiv.classList.add('loading');

        const messages = [
            { role: 'system', content: SYSTEM_PROMPTS.default },
            ...chatHistory.slice(-10),
        ];

        const result = await callAI(messages);

        loadingDiv.remove();

        if (result.error) {
            const errDiv = addMessage('ai', '❌ ' + result.error);
            errDiv.classList.add('error');
        } else {
            addMessage('ai', result.content);
            chatHistory.push({ role: 'assistant', content: result.content });
        }
    }

    async function handleQuickAction(action) {
        const prompts = {
            homework: SYSTEM_PROMPTS.homework,
            summary: SYSTEM_PROMPTS.summary,
            explain: SYSTEM_PROMPTS.explain,
            translate: SYSTEM_PROMPTS.translate,
        };

        const input = document.getElementById('xtai-input');
        const placeholder = {
            homework: '请粘贴题目内容...',
            summary: '已自动获取页面课程内容...',
            explain: '请输入想了解的概念...',
            translate: '请输入需要翻译的内容...',
        };

        input.placeholder = placeholder[action] || '';
        input.focus();

        CONFIG._quickMode = action;

        if (action === 'summary') {
            const pageContent = extractPageContent();
            input.value = '请总结当前页面的课程内容';
            if (pageContent) {
                input.value = `${SYSTEM_PROMPTS.summary}\n\n以下是课程内容：\n${pageContent.substring(0, 3000)}`;
                sendMessage();
                input.value = '';
            }
        }
    }

    // ========== 页面内容提取 ==========
    function extractPageContent() {
        const selectors = [
            '.ans-cc', '.ans-attach-cc', '.markdown-body',
            '.course-content', '.chapter-content', '#course_content',
            '.article-content', '.text-content', '.main-content',
            '.question-content', '.que-content',
        ];

        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.textContent.trim().length > 50) {
                return el.textContent.trim();
            }
        }

        const mainEl = document.querySelector('main, article, .content, #content');
        if (mainEl) {
            const text = mainEl.textContent.trim();
            if (text.length > 100) return text.substring(0, 3000);
        }

        return document.body.textContent.trim().substring(0, 2000);
    }

    // ========== 选中文字快捷操作 ==========
    function initTextSelectionToolbar() {
        let toolbar = null;

        document.addEventListener('mouseup', (e) => {
            const selection = window.getSelection();
            const text = selection.toString().trim();

            if (toolbar) toolbar.remove();

            if (text.length > 0 && text.length < 2000) {
                toolbar = document.createElement('div');
                toolbar.className = 'xtai-selected-text-toolbar';
                toolbar.innerHTML = '🤖 AI 问问';
                toolbar.style.left = e.pageX + 10 + 'px';
                toolbar.style.top = e.pageY - 30 + 'px';
                toolbar.style.display = 'block';

                toolbar.addEventListener('click', () => {
                    if (panelContainer.classList.contains('hidden')) {
                        panelContainer.classList.remove('hidden');
                        const fb = document.querySelector('.xtai-float-btn');
                        if (fb) fb.remove();
                    }
                    const input = document.getElementById('xtai-input');
                    input.value = text;
                    sendMessage();
                    toolbar.remove();
                });

                document.body.appendChild(toolbar);
            }
        });

        document.addEventListener('mousedown', (e) => {
            if (toolbar && !e.target.classList.contains('xtai-selected-text-toolbar')) {
                toolbar.remove();
                toolbar = null;
            }
        });
    }

    // ========== 快捷键 ==========
    function initShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.altKey && e.key === 'q') {
                e.preventDefault();
                if (panelContainer.classList.contains('hidden')) {
                    panelContainer.classList.remove('hidden');
                    const fb = document.querySelector('.xtai-float-btn');
                    if (fb) fb.remove();
                } else {
                    panelContainer.classList.add('hidden');
                    createFloatButton();
                }
            }
        });
    }

    // ========== 考试/作业自动答题 ==========
    function initAutoAnswer() {
        if (!CONFIG.enableAutoAnswer) return;

        const observer = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (node.nodeType === 1 && node.querySelector) {
                        checkForQuestions(node);
                    }
                }
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });

        setTimeout(checkForQuestions, 2000);

        // 添加自动答题按钮
        const addAutoBtn = setInterval(() => {
            const toolbarAreas = document.querySelectorAll('.CyToolbar, .questionToolbar, .exam-toolbar');
            for (const area of toolbarAreas) {
                if (area.querySelector('.xtai-auto-btn')) continue;
                const btn = document.createElement('button');
                btn.className = 'xtai-auto-btn';
                btn.textContent = '🤖 AI 答题';
                btn.style.cssText = 'margin-left:8px;padding:4px 12px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:4px;cursor:pointer;font-size:13px;';
                btn.addEventListener('click', () => autoAnswerAll());
                area.appendChild(btn);
            }
        }, 3000);

        setTimeout(() => clearInterval(addAutoBtn), 30000);
    }

    async function checkForQuestions(container) {
        const questions = container.querySelectorAll('.questionLi, .singleQuesId, .question-item, .queItem, [class*="question"]');
        for (const q of questions) {
            if (q.dataset.xtaiAnswered) continue;

            const titleEl = q.querySelector('.question-title, .q-title, .title, h4, h5, .mark_title');
            if (!titleEl) continue;

            const title = titleEl.textContent.trim();
            if (title.length < 5) continue;

            const optionsEls = q.querySelectorAll('.answerOption, .option, .options label, .answer-option, [class*="option"]');
            const options = [];
            optionsEls.forEach((opt) => {
                const text = opt.textContent.trim();
                if (text.length > 0) options.push(text);
            });

            q.dataset.xtaiAnswered = 'true';

            await answerQuestion(q, title, options);
        }
    }

    async function answerQuestion(container, title, options) {
        if (!CONFIG.apiKey) return;

        let prompt = `题目：${title}\n`;
        if (options.length > 0) {
            prompt += `选项：\n${options.map((o, i) => `${String.fromCharCode(65 + i)}. ${o}`).join('\n')}\n`;
        }
        prompt += '\n请给出正确答案，如果有选项请直接给出选项字母和答案。格式：答案：X';

        const messages = [
            { role: 'system', content: SYSTEM_PROMPTS.homework },
            { role: 'user', content: prompt },
        ];

        const result = await callAI(messages, { temperature: 0.3 });

        if (result.content && !result.error) {
            const answer = result.content.match(/答案[：:]\s*([A-Ea-e]|[A-Ea-e]\))/);
            if (answer) {
                const letter = answer[1].replace(/[\)）]/g, '').toUpperCase();
                const targetOption = container.querySelector(
                    `.answerOption:nth-child(${letter.charCodeAt(0) - 64}), ` +
                    `input[value="${letter}"], input[id*="${letter}"], ` +
                    `label:nth-of-type(${letter.charCodeAt(0) - 64}) input`
                );
                if (targetOption) {
                    targetOption.click();
                    targetOption.checked = true;
                    targetOption.dispatchEvent(new Event('change', { bubbles: true }));
                }

                // 高亮标记
                const marker = document.createElement('span');
                marker.style.cssText = 'margin-left:8px;color:#667eea;font-size:12px;';
                marker.textContent = `[AI: ${letter}]`;
                const titleEl = container.querySelector('.question-title, .q-title, .title, h4, h5');
                if (titleEl) titleEl.appendChild(marker);
            }
        }
    }

    async function autoAnswerAll() {
        if (!CONFIG.apiKey) {
            showToast('请先在设置中输入 API Key');
            return;
        }
        showToast('AI 正在答题中...');
        const questions = document.querySelectorAll('.questionLi, .singleQuesId, .question-item, .queItem, [class*="question"]');
        for (const q of questions) {
            await checkForQuestions(q);
        }
        showToast('答题完成！请人工核对答案');
    }

    // ========== 设置加载 ==========
    function loadSettings() {
        const saved = GM_getValue('ai_provider', '');
        if (saved) CONFIG.provider = saved;
        const key = GM_getValue('ai_api_key', '');
        if (key) CONFIG.apiKey = key;
    }

    // ========== 初始化 ==========
    function init() {
        createPanel();
        initShortcuts();
        initTextSelectionToolbar();
        initAutoAnswer();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
