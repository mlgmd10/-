# 学习通 AI 工具集

一套为**超星学习通网页版**定制的 AI 增强工具，通过油猴脚本 (Tampermonkey) 注入，无需安装任何软件即可使用。

## 📦 包含脚本

| 脚本 | 功能 | 推荐度 |
|------|------|--------|
| [ai-assistant.user.js](./ai-assistant.user.js) | AI 浮窗助手 + 作业自动答题 + 课程总结 + 翻译 | ⭐⭐⭐⭐⭐ |
| [quiz-helper.user.js](./quiz-helper.user.js) | 考试/测验专用快速答题器 | ⭐⭐⭐⭐ |
| [course-summarizer.user.js](./course-summarizer.user.js) | 一键生成课程笔记与思维导图 | ⭐⭐⭐⭐ |

## 🚀 快速开始

### 1. 安装 Tampermonkey

- [Chrome 版](https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo)
- [Edge 版](https://microsoftedge.microsoft.com/addons/detail/tampermonkey/iikmkjmpaadaobahmlepeloendndfphd)
- [Firefox 版](https://addons.mozilla.org/firefox/addon/tampermonkey/)

### 2. 安装脚本

点击下方链接安装（需先装好 Tampermonkey）：

- [安装 AI 智能助手](https://raw.githubusercontent.com/mlgmd10/-/master/xuetong-ai/ai-assistant.user.js)
- [安装 答题助手](https://raw.githubusercontent.com/mlgmd10/-/master/xuetong-ai/quiz-helper.user.js)
- [安装 课程总结器](https://raw.githubusercontent.com/mlgmd10/-/master/xuetong-ai/course-summarizer.user.js)

> 如果无法直接安装，打开 Tampermonkey 管理面板 → 新建脚本 → 复制脚本内容粘贴保存。

### 3. 配置 API Key

AI 功能需要 API Key，推荐以下免费/低成本方案：

| 提供商 | 获取地址 | 免费额度 | 推荐 |
|--------|---------|---------|------|
| **DeepSeek** | [platform.deepseek.com](https://platform.deepseek.com) | 注册送 500 万 tokens | ✅ 推荐 |
| Moonshot (Kimi) | [platform.moonshot.cn](https://platform.moonshot.cn) | 注册送 15 元 | ✅ |
| 智谱 GLM | [open.bigmodel.cn](https://open.bigmodel.cn) | 注册送额度 | ✅ |
| OpenAI | [platform.openai.com](https://platform.openai.com) | 需付费 | - |

获取后在脚本设置面板 (⚙) 中填入即可。

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Alt + Q` | 显示/隐藏 AI 面板 |
| `Enter` | 发送消息 |
| `Shift + Enter` | 换行 |
| 选中文字 | 弹出"AI 问问"快捷入口 |

## 🔧 功能详解

### AI 智能助手
- 浮动面板形式，可拖拽、最小化、关闭
- 四种快捷模式：作业助手 / 课程总结 / 概念讲解 / 翻译
- 选中网页文字即可调起 AI 问答
- 支持多轮对话，历史记录管理

### 作业自动答题
- 自动识别学习通页面中的选择题、判断题
- 调用 AI 给出答案并自动勾选
- 页面出现题目时自动触发
- 支持手动触发"AI 答题"按钮批量处理
- ⚠️ 建议答题后人工核对

### 课程内容总结
- 自动提取页面中的课程正文内容
- 生成结构化的知识点总结
- 支持长文本截断优化

## 📝 免责声明

本工具仅供学习辅助使用，请遵守学校规定和学术诚信准则。AI 生成的答案可能存在错误，使用前请人工核实。

## 📄 License

MIT
