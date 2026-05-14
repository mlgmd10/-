// ==UserScript==
// @name         学习通 答题助手
// @namespace    https://github.com/mlgmd10
// @version      1.2.0
// @description  专门用于考试/测验场景的快速答题器，支持选择题、判断题、填空题
// @author       GEO System
// @match        *://*.chaoxing.com/exam/*
// @match        *://*.chaoxing.com/mooc-ans/*
// @match        *://*.chaoxing.com/work/*
// @match        *://mooc1.chaoxing.com/exam/*
// @match        *://mooc1.chaoxing.com/mooc-ans/*
// @match        *://mooc1.chaoxing.com/work/*
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

    const API_KEY = GM_getValue('quiz_api_key', '');
    const PROVIDER = GM_getValue('quiz_provider', 'deepseek');

    const API_URLS = {
        deepseek: 'https://api.deepseek.com/v1/chat/completions',
        moonshot: 'https://api.moonshot.cn/v1/chat/completions',
        openai: 'https://api.openai.com/v1/chat/completions',
        glm: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    };

    GM_addStyle(`
        .qz-helper-bar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 20px;
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 14px;
            font-family: -apple-system, "Microsoft YaHei", sans-serif;
        }
        .qz-helper-bar button {
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.4);
            color: white;
            border-radius: 4px;
            padding: 5px 14px;
            margin-left: 8px;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.2s;
        }
        .qz-helper-bar button:hover {
            background: rgba(255,255,255,0.35);
        }
        .qz-helper-bar button.primary {
            background: #ff6b6b;
            border-color: #ff6b6b;
            font-weight: bold;
        }
        .qz-status {
            font-size: 12px;
            opacity: 0.9;
        }
        .qz-answered {
            outline: 2px solid #667eea !important;
            outline-offset: 2px;
        }
        .qz-mark {
            display: inline-block;
            margin-left: 6px;
            padding: 1px 6px;
            background: #667eea;
            color: white;
            border-radius: 3px;
            font-size: 11px;
        }
        .qz-error {
            outline: 2px solid #ff6b6b !important;
        }
        /* 防止顶栏遮挡 */
        body { padding-top: 44px !important; }
    `);

    // ========== API 调用 ==========
    function callAI(messages) {
        return new Promise((resolve) => {
            if (!API_KEY) {
                resolve({ error: '请先在顶栏设置 API Key' });
                return;
            }

            GM_xmlhttpRequest({
                method: 'POST',
                url: API_URLS[PROVIDER],
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${API_KEY}`,
                },
                data: JSON.stringify({
                    model: 'deepseek-chat',
                    messages: messages,
                    max_tokens: 500,
                    temperature: 0.2,
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
                timeout: 15000,
            });
        });
    }

    // ========== 题目识别 ==========
    function findAllQuestions() {
        const questions = [];

        const selectors = [
            '.questionLi', '.singleQuesId', '[class*="question"]',
            '.Cy_TItle', '.queLi', '.exam_question',
            '.tiItem', '.mark_item', '.question-content',
        ];

        const seen = new Set();

        for (const sel of selectors) {
            document.querySelectorAll(sel).forEach((el) => {
                if (seen.has(el)) return;
                seen.add(el);

                const titleEl = el.querySelector('.mark_title, .q-title, h3, h4, h5, .title, .question-title, p:first-child');
                const title = titleEl ? titleEl.textContent.trim() : el.textContent.trim().substring(0, 100);

                if (title.length < 3) return;

                const type = title.includes('判断') ? 'judge' :
                    title.includes('填空') ? 'fill' : 'choice';

                const options = [];
                el.querySelectorAll('label, .answerOption, .option, .ans-opt, .chooseOption, li[onclick]').forEach((opt) => {
                    const text = opt.textContent.trim().replace(/^\s*[A-Z][.、．]\s*/, '');
                    if (text.length > 0) options.push(text);
                });

                questions.push({ element: el, title, type, options });
            });
        }

        return questions;
    }

    // ========== 自动答题 ==========
    async function answerQuestion(q) {
        return new Promise(async (resolve) => {
            const prompt = q.type === 'choice'
                ? `单选题：${q.title}\n选项：${q.options.map((o, i) => `${String.fromCharCode(65 + i)}. ${o}`).join('\n')}\n请直接回复答案选项字母（如：A）`
                : q.type === 'judge'
                    ? `判断题：${q.title}\n请直接回复"对"或"错"`
                    : `填空题：${q.title}\n请直接回复答案内容`;

            const result = await callAI([
                { role: 'system', content: '你是答题助手。请简洁准确地给出答案，不要解释。' },
                { role: 'user', content: prompt },
            ]);

            if (result.content && !result.error) {
                markAnswer(q.element, result.content, q);
                q.element.classList.add('qz-answered');
            } else if (result.error) {
                q.element.classList.add('qz-error');
            }
            resolve();
        });
    }

    function markAnswer(element, answer, q) {
        const answerText = answer.trim();

        if (q.type === 'choice') {
            const match = answerText.match(/[A-Ea-e]/);
            if (match) {
                const letter = match[0].toUpperCase();
                const index = letter.charCodeAt(0) - 65;

                // 尝试多种选择器匹配选项
                const inputs = element.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                if (inputs[index]) {
                    inputs[index].click();
                    inputs[index].checked = true;
                    inputs[index].dispatchEvent(new Event('change', { bubbles: true }));
                }

                const labels = element.querySelectorAll('label');
                if (labels[index]) {
                    const radio = labels[index].querySelector('input');
                    if (radio) {
                        radio.click();
                        radio.checked = true;
                    }
                }
            }
        } else if (q.type === 'judge') {
            const isRight = answerText.includes('对') || answerText.includes('正确');
            const inputs = element.querySelectorAll('input[type="radio"]');
            if (inputs.length >= 2) {
                inputs[isRight ? 0 : 1].click();
                inputs[isRight ? 0 : 1].checked = true;
            }
        } else if (q.type === 'fill') {
            const textareas = element.querySelectorAll('textarea, input[type="text"]');
            if (textareas.length > 0) {
                textareas[0].value = answerText.replace(/^答案[：:]\s*/, '');
                textareas[0].dispatchEvent(new Event('input', { bubbles: true }));
            }
        }

        // 标记
        const mark = document.createElement('span');
        mark.className = 'qz-mark';
        mark.textContent = `AI: ${answerText.substring(0, 15)}`;
        element.appendChild(mark);
    }

    // ========== UI ==========
    function createToolbar() {
        const bar = document.createElement('div');
        bar.className = 'qz-helper-bar';
        bar.innerHTML = `
            <div>
                <strong>🤖 答题助手</strong>
                <span class="qz-status" id="qz-status"></span>
            </div>
            <div>
                <button id="qz-answer-current">⚡ 答当前题</button>
                <button id="qz-answer-all" class="primary">🔥 一键答全部</button>
                <button id="qz-settings">⚙ 设置</button>
            </div>
            <div id="qz-settings-panel" style="display:none;position:fixed;top:50px;right:20px;background:white;padding:16px;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.2);color:#333;z-index:99999;width:300px;">
                <h4 style="margin:0 0 12px;">设置</h4>
                <label style="display:block;margin-bottom:8px;font-size:13px;">API Key
                    <input type="password" id="qz-apikey" style="width:100%;padding:4px 8px;border:1px solid #ddd;border-radius:4px;margin-top:2px;" placeholder="sk-...">
                </label>
                <button id="qz-save" style="background:#667eea;color:white;border:none;border-radius:4px;padding:6px 16px;cursor:pointer;font-size:13px;">保存</button>
                <button id="qz-close-settings" style="margin-left:8px;background:#eee;border:none;border-radius:4px;padding:6px 16px;cursor:pointer;font-size:13px;">关闭</button>
            </div>
        `;
        document.body.insertBefore(bar, document.body.firstChild);

        // Events
        document.getElementById('qz-answer-all').addEventListener('click', answerAll);
        document.getElementById('qz-answer-current').addEventListener('click', answerVisible);
        document.getElementById('qz-settings').addEventListener('click', () => {
            const panel = document.getElementById('qz-settings-panel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            document.getElementById('qz-apikey').value = API_KEY;
        });
        document.getElementById('qz-save').addEventListener('click', () => {
            const key = document.getElementById('qz-apikey').value.trim();
            GM_setValue('quiz_api_key', key);
            GM_setValue('quiz_provider', PROVIDER);
            API_KEY.length = 0;
            Object.assign(API_KEY, key);
            document.getElementById('qz-settings-panel').style.display = 'none';
            updateStatus('设置已保存');
        });
        document.getElementById('qz-close-settings').addEventListener('click', () => {
            document.getElementById('qz-settings-panel').style.display = 'none';
        });
    }

    function updateStatus(msg) {
        const el = document.getElementById('qz-status');
        if (el) el.textContent = ' ' + msg;
    }

    async function answerAll() {
        if (!API_KEY) {
            updateStatus('请先设置 API Key');
            return;
        }

        const questions = findAllQuestions();
        updateStatus(`找到 ${questions.length} 题，正在答题...`);

        let answered = 0;
        for (let i = 0; i < questions.length; i++) {
            updateStatus(`答题中 ${i + 1}/${questions.length}...`);
            await answerQuestion(questions[i]);
            answered++;
            // 小延迟避免请求过快
            await new Promise(r => setTimeout(r, 300));
        }

        updateStatus(`完成！已答 ${answered}/${questions.length} 题`);
    }

    async function answerVisible() {
        if (!API_KEY) {
            updateStatus('请先设置 API Key');
            return;
        }

        const questions = findAllQuestions();
        // 找当前可见的题目
        const visible = questions.filter(q => {
            const rect = q.element.getBoundingClientRect();
            return rect.top >= 0 && rect.top <= window.innerHeight;
        });

        if (visible.length === 0) {
            updateStatus('未找到可见题目');
            return;
        }

        for (const q of visible) {
            await answerQuestion(q);
        }
        updateStatus(`已答 ${visible.length} 题`);
    }

    // ========== 初始化 ==========
    function init() {
        createToolbar();

        if (API_KEY) {
            updateStatus('就绪 (Alt+A 全答)');
        } else {
            updateStatus('请先设置 API Key');
        }

        // 快捷键
        document.addEventListener('keydown', (e) => {
            if (e.altKey && e.key === 'a') {
                e.preventDefault();
                answerAll();
            } else if (e.altKey && e.key === 'q') {
                e.preventDefault();
                answerVisible();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
