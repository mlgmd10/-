"""
桌面 AI 助手 - 独立于浏览器，监考录屏不可见
Ctrl+Shift+A 唤出/隐藏 | Ctrl+Enter 发送 | Esc 隐藏
"""
import tkinter as tk
import json
import urllib.request
import urllib.error
import threading
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'api_key': '', 'provider': 'deepseek', 'model': 'deepseek-chat'}


def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


config = load_config()

API_URLS = {
    'deepseek': 'https://api.deepseek.com/v1/chat/completions',
    'moonshot': 'https://api.moonshot.cn/v1/chat/completions',
    'openai': 'https://api.openai.com/v1/chat/completions',
    'glm': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
}


def call_ai(question, system_prompt, callback):
    if not config['api_key']:
        callback('请先设置 API Key（点击 ⚙ 按钮）')
        return

    body = json.dumps({
        'model': config['model'],
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': question},
        ],
        'max_tokens': 800,
        'temperature': 0.3,
    }).encode('utf-8')

    url = API_URLS.get(config['provider'], API_URLS['deepseek'])
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {config['api_key']}",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            callback(data['choices'][0]['message']['content'])
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode('utf-8'))
            msg = err_body.get('error', {}).get('message', str(e))
        except Exception:
            msg = str(e)
        callback(f'API错误: {msg}')
    except Exception as e:
        callback(f'网络错误: {e}')


class AIWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('AI')
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.93)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 440, 340
        x = sw - w - 20
        y = sh - h - 70
        self.root.geometry(f'{w}x{h}+{x}+{y}')

        self.visible = False

        # 两个面板叠加，通过 lift/lower 切换
        self.main_frame = tk.Frame(self.root, bg='#f5f5f5')
        self.settings_frame = tk.Frame(self.root, bg='white')

        self._build_main()
        self._build_settings()

        self.main_frame.place(relwidth=1, relheight=1)
        self.settings_frame.place(relwidth=1, relheight=1)
        self.main_frame.lift()

        self._make_draggable()

        self.root.bind('<Escape>', lambda e: self.hide())
        self.root.withdraw()

    # ---- 主面板 ----
    def _build_main(self):
        # 标题栏
        bar = tk.Frame(self.main_frame, bg='#2d2d44', height=34)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        tk.Label(bar, text=' AI 助手', fg='white', bg='#2d2d44',
                 font=('Microsoft YaHei', 10, 'bold')).pack(side=tk.LEFT, padx=10)

        for text, cmd in [('⚙', self.show_settings), ('−', self.hide)]:
            tk.Button(bar, text=text, fg='white', bg='#2d2d44',
                      bd=0, font=('', 10), cursor='hand2', command=cmd,
                      activebackground='#3d3d54').pack(side=tk.RIGHT, padx=4)

        # 模式按钮
        mode_frame = tk.Frame(self.main_frame, bg='#f5f5f5')
        mode_frame.pack(fill=tk.X, padx=6, pady=(6, 0))
        self.mode_var = tk.StringVar(value='answer')
        modes = [
            ('答题', 'answer', '#4ecdc4'),
            ('解释', 'explain', '#45b7d1'),
            ('翻译', 'translate', '#96ceb4'),
        ]
        for text, val, color in modes:
            rb = tk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=val,
                                indicatoron=0, font=('', 9), bg='#e8e8e8',
                                fg='#555', selectcolor=color, bd=0, padx=10,
                                activebackground=color, cursor='hand2')
            rb.pack(side=tk.LEFT, padx=(0, 4))

        # 输入区
        self.input_box = tk.Text(self.main_frame, height=2, font=('Microsoft YaHei', 11),
                                 wrap=tk.WORD, relief=tk.FLAT, borderwidth=1,
                                 bg='white', fg='#333', padx=8, pady=6)
        self.input_box.pack(fill=tk.X, padx=6, pady=(6, 0))
        self.input_box.insert('1.0', '输入题目或问题...')
        self.input_box.bind('<Button-1>', self._clear_placeholder)
        self.input_box.bind('<FocusIn>', self._clear_placeholder)

        # 发送按钮
        btn_frame = tk.Frame(self.main_frame, bg='#f5f5f5')
        btn_frame.pack(fill=tk.X, padx=6, pady=(4, 0))

        self.send_btn = tk.Button(btn_frame, text='Ctrl+Enter 发送', bg='#667eea', fg='white',
                                  font=('', 10, 'bold'), relief=tk.FLAT,
                                  cursor='hand2', command=self.ask, padx=12)
        self.send_btn.pack(side=tk.RIGHT)
        self.root.bind('<Control-Return>', lambda e: self.ask())

        # 输出区
        self.output_box = tk.Text(self.main_frame, font=('Microsoft YaHei', 11),
                                  wrap=tk.WORD, relief=tk.FLAT, borderwidth=0,
                                  bg='white', fg='#333', padx=10, pady=8,
                                  state=tk.DISABLED)
        self.output_box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 复制按钮
        tk.Button(self.main_frame, text='复制答案', bg='#e8e8e8', fg='#555',
                  font=('', 9), relief=tk.FLAT, cursor='hand2',
                  command=self.copy_answer).pack(pady=(0, 6))

        # 状态栏
        self.status_lbl = tk.Label(self.main_frame,
                                   text='Ctrl+Shift+A 唤出 | Ctrl+Enter 发送 | Esc 隐藏',
                                   fg='#aaa', bg='#f5f5f5', font=('', 8))
        self.status_lbl.pack(fill=tk.X, padx=10, pady=(0, 4))

    # ---- 设置面板 ----
    def _build_settings(self):
        tk.Label(self.settings_frame, text='⚙ 设置', font=('', 12, 'bold'),
                 bg='white').pack(anchor=tk.W, padx=14, pady=(14, 10))

        tk.Label(self.settings_frame, text='API Key (DeepSeek 免费注册即得)', font=('', 9),
                 fg='#666', bg='white').pack(anchor=tk.W, padx=14)
        self.api_key_entry = tk.Entry(self.settings_frame, show='*', font=('', 10))
        self.api_key_entry.pack(fill=tk.X, padx=14, pady=(4, 4))
        self.api_key_entry.insert(0, config.get('api_key', ''))

        tk.Label(self.settings_frame, text='获取地址: platform.deepseek.com → API Keys',
                 font=('', 8), fg='#999', bg='white', cursor='hand2').pack(anchor=tk.W, padx=14)

        btn_frame = tk.Frame(self.settings_frame, bg='white')
        btn_frame.pack(fill=tk.X, padx=14, pady=(14, 0))
        tk.Button(btn_frame, text='保存', bg='#667eea', fg='white',
                  font=('', 10, 'bold'), relief=tk.FLAT, padx=16,
                  command=self.save_settings).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_frame, text='取消', bg='#ddd', fg='#333',
                  font=('', 10), relief=tk.FLAT, padx=16,
                  command=self.show_main).pack(side=tk.LEFT)

        tk.Label(self.settings_frame, text='\n快捷键: Ctrl+Shift+A 唤出/隐藏\n'
                 '发送: Ctrl+Enter   隐藏: Esc\n'
                 '⚠ 本工具不注入浏览器，监考录屏不可见',
                 font=('', 8), fg='#bbb', bg='white', justify=tk.LEFT).pack(
                     anchor=tk.W, padx=14, pady=(20, 0))

    def _clear_placeholder(self, event=None):
        if self.input_box.get('1.0', 'end-1c') == '输入题目或问题...':
            self.input_box.delete('1.0', tk.END)

    def show_settings(self):
        self.settings_frame.lift()
        self.api_key_entry.delete(0, tk.END)
        self.api_key_entry.insert(0, config.get('api_key', ''))

    def show_main(self):
        self.main_frame.lift()

    def save_settings(self):
        config['api_key'] = self.api_key_entry.get().strip()
        save_config(config)
        self.show_main()

    def ask(self):
        question = self.input_box.get('1.0', 'end-1c').strip()
        if not question or question == '输入题目或问题...':
            return
        self.input_box.delete('1.0', tk.END)

        mode = self.mode_var.get()
        prompts = {
            'answer': '你是答题助手。回答简洁准确。选择题只给答案字母，判断题只给对/错，简答题50字以内。',
            'explain': '你是知识讲解专家。用通俗易懂的语言解释概念，可以举例子帮助理解。',
            'translate': '你是翻译助手。把内容翻译成中文，保持原意，语言流畅。',
        }

        self._set_output('⏳ 思考中...')
        self.status_lbl.config(text='AI 生成中...')
        threading.Thread(
            target=call_ai,
            args=(question, prompts.get(mode, prompts['answer']), self._set_output),
            daemon=True,
        ).start()

    def _set_output(self, text):
        self.output_box.config(state=tk.NORMAL)
        self.output_box.delete('1.0', tk.END)
        self.output_box.insert('1.0', text)
        self.output_box.config(state=tk.DISABLED)
        self.status_lbl.config(text='Ctrl+Shift+A 唤出 | Ctrl+Enter 发送 | Esc 隐藏')

    def copy_answer(self):
        text = self.output_box.get('1.0', 'end-1c')
        if text and text != '⏳ 思考中...':
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_lbl.config(text='✓ 已复制到剪贴板')

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.input_box.focus_set()
        self.visible = True

    def hide(self):
        self.root.withdraw()
        self.visible = False

    def _make_draggable(self):
        def start_drag(e):
            self._dx, self._dy = e.x, e.y

        def do_drag(e):
            x = self.root.winfo_x() + e.x - self._dx
            y = self.root.winfo_y() + e.y - self._dy
            self.root.geometry(f'+{x}+{y}')

        # 拖拽仅限标题栏区域 (前34px)
        for frame in [self.main_frame, self.settings_frame]:
            frame.bind('<Button-1>', lambda e, f=frame: self._on_click(f, e))
        self.root.bind('<B1-Motion>', self._on_drag)

    def _on_click(self, frame, e):
        # 只在标题栏区域响应拖拽
        if e.y <= 34:
            self._dx, self._dy = e.x, e.y
            self._dragging = True
        else:
            self._dragging = False

    def _on_drag(self, e):
        if getattr(self, '_dragging', False):
            x = self.root.winfo_x() + e.x - self._dx
            y = self.root.winfo_y() + e.y - self._dy
            self.root.geometry(f'+{x}+{y}')

    def run(self):
        self.root.mainloop()


def start_hotkey(window):
    try:
        from pynput import keyboard
    except ImportError:
        print('[!] 需要 pynput: pip install pynput')
        return None

    def on_activate():
        window.root.after(0, window.toggle)

    hk = keyboard.GlobalHotKeys({'<ctrl>+<shift>+a': on_activate})
    hk.start()
    return hk


def main():
    print('=' * 45)
    print('  AI 桌面助手 v1.0')
    print('  独立于浏览器运行，监考录屏不可见')
    print('=' * 45)
    print('  Ctrl+Shift+A  唤出/隐藏')
    print('  Ctrl+Enter    发送问题')
    print('  Esc           隐藏窗口')
    print('')
    print('  首次使用请设置 API Key:')
    print('  1. 打开 https://platform.deepseek.com')
    print('  2. 注册 → API Keys → 创建 Key')
    print('  3. 在此窗口点击 ⚙ 填入 Key')
    print('=' * 45)

    window = AIWindow()

    hotkey = start_hotkey(window)
    if hotkey:
        print('[OK] 全局快捷键已注册')
    else:
        print('[!] 快捷键不可用，请手动操作窗口')

    try:
        import pystray
        from PIL import Image, ImageDraw

        icon_img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon_img)
        draw.ellipse([8, 8, 56, 56], fill='#667eea')
        draw.text((18, 17), 'AI', fill='white')

        menu = pystray.Menu(
            pystray.MenuItem('显示/隐藏', lambda: window.root.after(0, window.toggle), default=True),
            pystray.MenuItem('设置', lambda: window.root.after(0, window.show_settings)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('退出',
                             lambda: (hotkey.stop() if hotkey else None,
                                      tray.stop(),
                                      window.root.after(0, window.root.destroy))),
        )
        tray = pystray.Icon('ai_desk', icon_img, 'AI 助手', menu)
        threading.Thread(target=tray.run, daemon=True).start()
        print('[OK] 系统托盘已创建')
    except ImportError:
        print('[!] pystray/pillow 未安装，托盘不可用 (pip install pystray pillow)')
        print('[!] 窗口将直接显示，手动操作即可')
        window.show()

    window.run()


if __name__ == '__main__':
    main()
