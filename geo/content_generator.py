import json
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("geo.generator")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class ContentPiece:
    id: str
    title: str
    body: str
    topic: str
    content_type: str
    seo_keywords: List[str]
    target_platforms: List[str]
    quality_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "draft"

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "topic": self.topic,
            "content_type": self.content_type,
            "seo_keywords": self.seo_keywords,
            "target_platforms": self.target_platforms,
            "quality_score": self.quality_score,
            "created_at": self.created_at,
            "status": self.status,
        }


class ContentGenerator:
    """内容生成引擎：结合选题、prompt模板、多版本生成"""

    PROMPT_TEMPLATES = {
        "tutorial": {
            "system": "你是一个资深技术博主，擅长将复杂概念讲得通俗易懂。",
            "user": "请写一篇关于「{topic}」的实战教程。要求：{requirements}",
            "default_requirements": "包含至少3个步骤，每个步骤有代码示例，字数2000-3000字",
        },
        "insight": {
            "system": "你是一个行业分析师，善于从数据中提炼洞见。",
            "user": "请写一篇关于「{topic}」的深度分析文章。要求：{requirements}",
            "default_requirements": "引用数据支撑，提出3个核心观点，字数1500-2500字",
        },
        "list": {
            "system": "你是一个内容策划，擅长制作高传播度的列表型内容。",
            "user": "请写一篇关于「{topic}」的推荐列表。要求：{requirements}",
            "default_requirements": "列出10个推荐项，每项有简短说明，总字数1000-1500字",
        },
        "news": {
            "system": "你是一个科技媒体编辑，对行业动态嗅觉敏锐。",
            "user": "请写一篇关于「{topic}」的新闻解读。要求：{requirements}",
            "default_requirements": "分析事件影响，预测发展趋势，字数800-1200字",
        },
        "qa": {
            "system": "你是一个知识分享达人，擅长用问答形式解决读者疑惑。",
            "user": "请以问答形式写一篇关于「{topic}」的答疑文章。要求：{requirements}",
            "default_requirements": "至少5个问答，每个150-300字，总字数1500-2000字",
        },
    }

    def __init__(self, config=None):
        self.config = config
        self.generated: List[ContentPiece] = []
        self.prompt_performance: Dict[str, List[Dict]] = {}

    def generate(self, topic: Dict, content_type: Optional[str] = None, platform: Optional[str] = None) -> ContentPiece:
        """根据话题生成内容"""
        keyword = topic.get("keyword", "通用主题")
        ct = content_type or topic.get("content_type", "tutorial")
        logger.info(f"[Generator] 生成内容: {keyword} [{ct}]")

        prompt_template = self.PROMPT_TEMPLATES.get(ct, self.PROMPT_TEMPLATES["tutorial"])
        requirements = self._build_requirements(ct, platform)

        title = self._generate_title(keyword, ct)
        body = self._generate_body(keyword, ct, prompt_template, requirements)
        seo_keywords = self._extract_keywords(keyword, ct)
        target_platforms = topic.get("platforms", ["zhihu", "csdn"])

        content = ContentPiece(
            id=f"content_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100, 999)}",
            title=title,
            body=body,
            topic=keyword,
            content_type=ct,
            seo_keywords=seo_keywords,
            target_platforms=target_platforms,
        )

        self.generated.append(content)
        self._save_content(content)
        return content

    def batch_generate(self, topics: List[Dict], count: Optional[int] = None) -> List[ContentPiece]:
        """批量生成内容"""
        results = []
        limit = count or len(topics)
        for topic in topics[:limit]:
            content = self.generate(topic)
            results.append(content)
        logger.info(f"[Generator] 批量生成完成: {len(results)} 条内容")
        return results

    def _generate_title(self, keyword: str, content_type: str) -> str:
        title_templates = {
            "tutorial": [
                "【实战教程】{keyword}完全指南：从零到精通",
                "手把手教你{keyword}：保姆级入门教程",
                "{keyword}实战：看完这篇就够了",
                "5分钟掌握{keyword}核心技巧",
            ],
            "insight": [
                "深度解析{keyword}：为什么它正在改变一切",
                "{keyword}背后的底层逻辑，90%的人没看懂",
                "关于{keyword}，你可能不知道的3个真相",
                "从数据看{keyword}：未来3年的趋势预测",
            ],
            "list": [
                "2024年{keyword}必看：10个不可错过的资源合集",
                "{keyword}最全推荐清单：从工具到方法论",
                "提升{keyword}效率的7个神器，第5个太实用了",
            ],
            "news": [
                "刚刚！{keyword}领域迎来重大更新",
                "{keyword}最新动态：这意味着什么？",
            ],
            "qa": [
                "{keyword}高频20问：你想知道的都在这里",
                "关于{keyword}的10个灵魂拷问，一篇文章全解答",
                "{keyword}入门必看：最常见的8个问题答案",
            ],
        }

        templates = title_templates.get(content_type, title_templates["tutorial"])
        title = random.choice(templates).replace("{keyword}", keyword)
        return title

    def _generate_body(self, keyword: str, content_type: str, template: Dict, requirements: str) -> str:
        """模拟内容生成 (实际应调用 LLM API)"""
        paragraphs = []

        paragraphs.append(f"# {self._generate_title(keyword, content_type)}\n")

        intro_variants = [
            f"在当今快速发展的技术生态中，{keyword}已经成为一个绕不开的关键话题。无论你是刚入门的新手还是经验丰富的老手，本文都将为你提供系统性的解决方案。\n",
            f"你是否在寻找关于{keyword}的全面指南？本文将从一个全新的视角，带你深入理解{keyword}的核心原理与最佳实践。\n",
        ]
        paragraphs.append(random.choice(intro_variants))

        if content_type == "tutorial":
            paragraphs.append("## 一、背景与原理\n")
            paragraphs.append(f"{keyword}的底层机制可以概括为三个核心层次：数据层、逻辑层和展示层。理解这三层之间的关系是掌握{keyword}的第一步。\n")

            paragraphs.append("## 二、实战步骤\n")

            sub_topics = ["环境准备与工具安装", f"{keyword}基础概念解析", "核心功能实现", "错误排查与调试技巧", "性能优化最佳实践"]
            for i, sub in enumerate(sub_topics, 1):
                paragraphs.append(f"### {i}. {sub}\n")
                paragraphs.append(f"在{keyword}的实战中，{sub}是至关重要的一环。以下是一个完整的示例：\n\n```python\n# {keyword} 示例代码\nimport example\nresult = example.process('{keyword}')\nprint(f'处理结果: {{result}}')\n```\n\n这段代码展示了{keyword}的核心操作流程，通过几个关键步骤即可完成复杂的处理任务。\n")

            paragraphs.append("## 三、常见问题与解决方案\n")

            faqs = [
                (f"Q: {keyword}适合新手吗？", f"A: 是的，{keyword}设计了友好的入门路径，建议从基础概念开始学习。"),
                (f"Q: {keyword}性能如何优化？", "A: 性能优化需要从数据结构、算法选择和缓存策略三个维度综合考虑。"),
                (f"Q: 有推荐的{keyword}学习资源吗？", "A: 建议结合官方文档和实战项目，同时关注行业最新动态。"),
            ]
            for q, a in faqs:
                paragraphs.append(f"{q}\n{a}\n")

            paragraphs.append("## 四、总结\n")
            paragraphs.append(f"掌握{keyword}需要理论与实践相结合。本文从基础原理到高级应用，为你搭建了完整的知识框架。持续实践、保持好奇，你将在{keyword}领域不断精进。\n")

        elif content_type == "insight":
            paragraphs.append("## 核心观点\n")
            paragraphs.append(f"1. **{keyword}正在重塑行业格局** —— 传统模式面临颠覆，新技术路径正在形成\n")
            paragraphs.append(f"2. **数据驱动{keyword}的效率革命** —— 量化分析揭示隐藏的增长机会\n")
            paragraphs.append(f"3. **{keyword}的人才缺口持续扩大** —— 掌握相关技能将获得显著竞争优势\n")

            paragraphs.append("## 数据与证据\n")
            paragraphs.append(f"根据行业数据显示，{keyword}相关职位需求在过去一年增长了145%。同时，运用{keyword}的企业平均效率提升达3.2倍。这些数据清楚地表明，{keyword}已从可选技能变为必备能力。\n")

            paragraphs.append("## 趋势预测\n")
            paragraphs.append(f"展望未来，{keyword}将向三个方向演进：智能化、自动化和个性化。企业应提前布局，抢占先机。\n")

        elif content_type == "list":
            paragraphs.append("## 精选推荐\n")
            items = [
                f"工具A：专为{keyword}设计的效率工具，支持一键操作",
                f"网站B：{keyword}领域最活跃的社区，日活10万+",
                f"课程C：从入门到精通{keyword}的系统课程",
                f"书籍D：{keyword}领域的经典之作",
                f"框架E：基于{keyword}的开源框架，Github Star 10k+",
                f"插件F：提升{keyword}开发效率的必备插件",
                f"平台G：{keyword}垂直领域的专业平台",
                f"模板H：{keyword}项目快速启动模板",
            ]
            for i, item in enumerate(items, 1):
                paragraphs.append(f"{i}. {item}\n")

        elif content_type == "qa":
            paragraphs.append("## 常见问答\n")
            qas = [
                (f"Q1: {keyword}是什么？", f"A: {keyword}是一种融合了多种技术手段的解决方案，在自动化、数据分析等领域有广泛应用。它的核心价值在于提升效率、降低成本。"),
                (f"Q2: 新手如何入门{keyword}？", f"A: 建议从官方文档入手，结合小型实战项目练习。推荐每天投入1-2小时，两周内可掌握基础操作。"),
                (f"Q3: {keyword}有哪些常见误区？", f"A: 最大的误区是认为{keyword}可以解决一切问题。实际上它更适合特定场景，需要结合实际需求评估。"),
                (f"Q4: {keyword}的未来趋势如何？", f"A: 据行业分析，{keyword}正朝着智能化、低代码化和云原生化方向发展，预计未来3年市场规模增长200%。"),
                (f"Q5: 有哪些{keyword}学习资源推荐？", f"A: 推荐官方文档、知名技术博客、开源社区以及实战课程。建议从经典资源开始，逐渐形成自己的知识体系。"),
                (f"Q6: {keyword}在实际项目中的应用场景？", f"A: 可应用于自动化部署、数据分析、内容管理等多个场景。关键在于找到与业务痛点匹配的切入点。"),
            ]
            for q, a in qas:
                paragraphs.append(f"**{q}**\n\n{a}\n")

        paragraphs.append("\n---\n")
        paragraphs.append(f"*本文由 GEO 自动化系统生成，持续优化中*")

        return "\n".join(paragraphs)

    def _build_requirements(self, content_type: str, platform: Optional[str] = None) -> str:
        template = self.PROMPT_TEMPLATES.get(content_type, {})
        base = template.get("default_requirements", "内容丰富，结构清晰")

        platform_reqs = {
            "zhihu": "语气专业且有个人观点，适合引发讨论",
            "csdn": "技术深度优先，代码示例详细",
            "toutiao": "通俗易懂，加入趣味性表达",
            "xiaohongshu": "轻松口语化，多使用emoji",
            "wechat_mp": "正式且深度，适合深度阅读",
        }

        if platform:
            base += f"，{platform_reqs.get(platform, '')}"

        return base

    def _extract_keywords(self, keyword: str, content_type: str) -> List[str]:
        base_kw = [keyword]
        suffix_map = {
            "tutorial": ["教程", "入门", "实战", "指南", "详解"],
            "insight": ["分析", "趋势", "深度", "解读", "观点"],
            "list": ["推荐", "合集", "排名", "清单"],
            "news": ["最新", "动态", "更新", "解读"],
            "qa": ["问题", "答疑", "问答", "FAQ"],
        }
        suffixes = suffix_map.get(content_type, ["教程", "指南"])
        long_tail = [f"{keyword}{s}" for s in suffixes]
        return base_kw + long_tail

    def _save_content(self, content: ContentPiece):
        output_path = DATA_DIR / "content" / f"{content.id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(content.to_dict(), f, ensure_ascii=False, indent=2)

    def update_prompt_from_feedback(self, content_type: str, metrics: Dict):
        """根据反馈数据优化 Prompt 模板"""
        if content_type not in self.prompt_performance:
            self.prompt_performance[content_type] = []
        self.prompt_performance[content_type].append(metrics)

        if len(self.prompt_performance[content_type]) >= 5:
            recent = self.prompt_performance[content_type][-5:]
            avg_ctr = sum(m.get("ctr", 0) for m in recent) / len(recent)

            if avg_ctr < 0.03 and content_type in self.PROMPT_TEMPLATES:
                self.PROMPT_TEMPLATES[content_type]["default_requirements"] += "，增强标题吸引力，首段增加钩子"
                logger.info(f"[Generator] Prompt 已优化: {content_type}, 平均CTR={avg_ctr:.3f}")
