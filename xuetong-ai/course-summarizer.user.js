// ==UserScript==
// @name         学习通 课程总结器
// @namespace    https://github.com/mlgmd10
// @version      1.1.0
// @description  一键提取课程内容并生成结构化笔记与思维导图(Markdown格式)
// @author       GEO System
// @match        *://*.chaoxing.com/mycourse/*
// @match        *://*.chaoxing.com/course/*
// @match        *://mooc1.chaoxing.com/mycourse/*
// @match        *://mooc1.chaoxing.com/course/*
// @match        *://i.chaoxing.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_addStyle
// @connect      api.deepseek.com
// @connect      api.moonshot.cn
// @connect      api.openai.com
// @connect      open.bigmodel.cn
// @run-at       document-end
// ==/UserScript==

(function () {
    'use strict';

    const API_KEY = GM_getValue('sum_api_key', GM_getValue('quiz_api_key', ''));
    const PROVIDER = GM_getValue('sum_provider', 'deepseek');

    GM_addStyle(`
        .sum-panel {
            position: fixed;
            right: 0;
            top: 0;
            width: 420px;
            height: 100vh;
            background: white;
            box-shadow: -4px 0 20px rgba(0,0,0,0.12);
            z-index: 99999;
            display: flex;
            flex-direction: column;
            font-family: -apple-system, "Microsoft YaHei", sans-serif;
            font-size: 14px;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        }
        .sum-panel.open {
            transform: translateX(0);
        }
        .sum-header {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
        }
        .sum-header button {
            background: rgba(255,255,255,0.25);
            border: none;
            color: white;
            border-radius: 4px;
            padding: 4px 10px;
            cursor: pointer;
            font-size: 13px;
        }
        .sum-body {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            line-height: 1.7;
            color: #333;
        }
        .sum-body h1 { font-size: 18px; color: #11998e; border-bottom: 2px solid #eee; padding-bottom: 6px; }
        .sum-body h2 { font-size: 16px; color: #333; margin-top: 16px; }
        .sum-body h3 { font-size: 14px; color: #555; }
        .sum-body ul, .sum-body ol { padding-left: 20px; }
        .sum-body code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
        .sum-body pre { background: #2d2d2d; color: #f8f8f2; padding: 12px; border-radius: 6px; overflow-x: auto; }
        .sum-body blockquote { border-left: 3px solid #11998e; padding-left: 12px; color: #666; margin: 12px 0; }
        .sum-toolbar {
            padding: 10px 16px;
            border-bottom: 1px solid #eee;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .sum-toolbar button {
            padding: 6px 14px;
            border: 1px solid #ddd;
            border-radius: 16px;
            background: white;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        .sum-toolbar button:hover {
            border-color: #11998e;
            color: #11998e;
            background: #f0fff4;
        }
        .sum-toolbar button.active {
            background: #11998e;
            color: white;
            border-color: #11998e;
        }
        .sum-toggle {
            position: fixed;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            border: none;
            border-radius: 8px 0 0 8px;
            padding: 12px 8px;
            cursor: pointer;
            z-index: 99998;
            writing-mode: vertical-lr;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 2px;
            transition: right 0.3s;
        }
        .sum-toggle.hidden {
            right: 420px;
        }
        .sum-loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 200px;
            color: #999;
        }
        .sum-spinner {
            width: 32px;
            height: 32px;
            border: 3px solid #eee;
            border-top-color: #11998e;
            border-radius: 50%;
            animation: sum-spin 0.8s linear infinite;
        }
        @keyframes sum-spin { to { transform: rotate(360deg); } }
        .sum-export-btn {
            display: inline-block;
            padding: 4px 12px;
            background: #11998e;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-top: 12px;
        }
    `);

    // ========== API 调用 ==========
    function callAI(messages) {
        return new Promise((resolve) => {
            if (!API_KEY) {
                resolve({ error: '请先设置 API Key' });
                return;
            }

            const urls = {
                deepseek: 'https://api.deepseek.com/v1/chat/completions',
                moonshot: 'https://api.moonshot.cn/v1/chat/completions',
                openai: 'https://api.openai.com/v1/chat/completions',
                glm: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            };

            GM_xmlhttpRequest({
                method: 'POST',
                url: urls[PROVIDER] || urls.deepseek,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${API_KEY}`,
                },
                data: JSON.stringify({
                    model: 'deepseek-chat',
                    messages: messages,
                    max_tokens: 2000,
                    temperature: 0.5,
                }),
                onload: (r) => {
                    try {
                        const d = JSON.parse(r.responseText);
                        resolve({ content: d.choices?.[0]?.message?.content || '' });
                    } catch (e) {
                        resolve({ error: '解析失败' });
                    }
                },
                onerror: () => resolve({ error: '网络错误' }),
                timeout: 25000,
            });
        });
    }

    // ========== 内容提取 ==========
    function extractContent() {
        const selectors = [
            '.ans-cc', '.ans-attach-cc', '.markdown-body',
            '.course-content', '.chapter-content', '#course_content',
            '.article-content', '.text-content',
            '.ppt_content', '.slide-content',
        ];

        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.textContent.trim().length > 100) {
                return el.textContent.trim();
            }
        }

        // 尝试提取 iframe 内容
        const iframe = document.querySelector('iframe[src*="ppt"], iframe[src*="chapter"], iframe[src*="course"]');
        if (iframe && iframe.contentDocument) {
            const text = iframe.contentDocument.body.textContent.trim();
            if (text.length > 100) return text;
        }

        // 回退方案
        const main = document.querySelector('main, article, .content, #content');
        if (main) {
            const text = main.textContent.trim();
            if (text.length > 100) return text.substring(0, 5000);
        }

        return '';
    }

    function buildPrompt(content, style) {
        const prefixes = {
            summary: `请用中文总结以下课程内容，提取3-5个核心知识点。每个知识点用一句话概括。`,
            detailed: `请用中文详细总结以下课程内容，使用 Markdown 格式。包括：\n` +
                `1. 核心知识点（分点列出）\n2. 重要概念解释\n3. 关键结论\n4. 可能的考点提示`,
            mindmap: `请用 Markdown 多级列表格式为以下课程内容生成思维导图结构。最多3级嵌套，每个节点简洁明了。`,
            keypoints: `请提取以下课程内容的考点清单，用列表列出可能的考试重点，每题附简短答案。`,
        };

        return prefixes[style] + '\n\n' + content.substring(0, 4000);
    }

    // ========== UI ==========
    function createPanel() {
        const panel = document.createElement('div');
        panel.className = 'sum-panel';
        panel.innerHTML = `
            <div class="sum-header">
                <span>📋 课程总结器</span>
                <div>
                    <button id="sum-settings-btn">⚙</button>
                    <button id="sum-close-btn">✕</button>
                </div>
            </div>
            <div class="sum-toolbar">
                <button class="active" data-style="summary">📝 精简总结</button>
                <button data-style="detailed">📖 详细笔记</button>
                <button data-style="mindmap">🧠 思维导图</button>
                <button data-style="keypoints">🎯 考点提取</button>
            </div>
            <div class="sum-body" id="sum-body">
                <div class="sum-loading">
                    <p>👈 点击左侧按钮生成课程总结</p>
                    <p style="font-size:12px;color:#bbb;">自动识别当前页面课程内容</p>
                </div>
            </div>
        `;
        document.body.appendChild(panel);

        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'sum-toggle';
        toggleBtn.textContent = '课程总结';
        document.body.appendChild(toggleBtn);

        // Events
        toggleBtn.addEventListener('click', () => {
            panel.classList.toggle('open');
            toggleBtn.classList.toggle('hidden');
        });

        document.getElementById('sum-close-btn').addEventListener('click', () => {
            panel.classList.remove('open');
            toggleBtn.classList.remove('hidden');
        });

        // 工具栏按钮
        document.querySelectorAll('.sum-toolbar button').forEach((btn) => {
            btn.addEventListener('click', async function () {
                document.querySelectorAll('.sum-toolbar button').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                const style = this.dataset.style;
                const body = document.getElementById('sum-body');
                body.innerHTML = '<div class="sum-loading"><div class="sum-spinner"></div><p>AI 正在生成...</p></div>';

                if (!API_KEY) {
                    body.innerHTML = '<div class="sum-loading"><p>❌ 请先设置 API Key (点击右上角 ⚙)</p></div>';
                    return;
                }

                const content = extractContent();
                if (!content) {
                    body.innerHTML = '<div class="sum-loading"><p>⚠️ 未检测到课程内容，请在课程页面使用此功能</p></div>';
                    return;
                }

                const prompt = buildPrompt(content, style);
                const result = await callAI([
                    { role: 'system', content: '你是课程笔记助手。输出使用中文，格式整洁，使用 Markdown 语法。' },
                    { role: 'user', content: prompt },
                ]);

                if (result.content && !result.error) {
                    body.innerHTML = result.content.replace(/\n/g, '<br>')
                        .replace(/^#{1,3}\s(.+)/gm, (_, t) => `<h${_.split('#').length - 1}>${t}</h${_.split('#').length - 1}>`)
                        .replace(/^\*\s(.+)/gm, '<li>$1</li>')
                        .replace(/^- (.+)/gm, '<li>$1</li>')
                        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                        .replace(/`([^`]+)`/g, '<code>$1</code>');

                    // 添加导出按钮
                    const exportBtn = document.createElement('button');
                    exportBtn.className = 'sum-export-btn';
                    exportBtn.textContent = '📥 复制 Markdown';
                    exportBtn.addEventListener('click', () => {
                        navigator.clipboard.writeText(result.content).then(() => {
                            exportBtn.textContent = '✓ 已复制';
                            setTimeout(() => exportBtn.textContent = '📥 复制 Markdown', 2000);
                        });
                    });
                    body.appendChild(exportBtn);
                } else {
                    body.innerHTML = `<div class="sum-loading"><p>❌ ${result.error || '生成失败'}</p></div>`;
                }
            });
        });

        // 设置
        document.getElementById('sum-settings-btn').addEventListener('click', () => {
            const body = document.getElementById('sum-body');
            body.innerHTML = `
                <h3>⚙ 设置</h3>
                <label style="display:block;margin:12px 0;">API Key
                    <input type="password" id="sum-apikey" value="${API_KEY}" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:4px;margin-top:4px;" placeholder="sk-...">
                </label>
                <p style="font-size:11px;color:#999;">与 AI 助手/AI 答题共享 Key 即可</p>
                <button id="sum-save-btn" class="sum-export-btn">保存</button>
            `;
            document.getElementById('sum-save-btn').addEventListener('click', () => {
                const key = document.getElementById('sum-apikey').value.trim();
                GM_setValue('sum_api_key', key);
                GM_setValue('sum_provider', PROVIDER);
                body.innerHTML = '<div class="sum-loading"><p>✓ 设置已保存</p></div>';
            });
        });

        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 's') {
                if (document.activeElement === document.body) {
                    e.preventDefault();
                    panel.classList.toggle('open');
                    toggleBtn.classList.toggle('hidden');
                }
            }
        });
    }

    // ========== 初始化 ==========
    function init() {
        createPanel();
        console.log('[课程总结器] 已加载 | Ctrl+S 切换面板');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
