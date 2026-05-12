import json
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("geo.executor")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "data" / "templates"


@dataclass
class ExecutionResult:
    step_action: str
    success: bool
    output: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ExecutorAgent:
    """内容生成与操作执行 Agent"""

    CONTENT_TEMPLATES = {
        "tutorial": {
            "structure": ["标题", "引言", "背景说明", "分步讲解{steps}", "代码示例{code_blocks}", "常见问题", "总结"],
            "style": "专业、清晰、循序渐进",
            "seo_keywords": ["教程", "入门", "实战", "详解", "指南"],
        },
        "insight": {
            "structure": ["标题(观点型)", "开篇钩子", "核心观点", "论据展开", "数据支撑", "案例引用", "总结升华"],
            "style": "犀利、有洞见、逻辑严密",
            "seo_keywords": ["深度分析", "趋势", "洞察", "本质", "底层逻辑"],
        },
        "list": {
            "structure": ["标题(数字+价值)", "一句话摘要", "列表条目 x N", "每个条目的简要说明", "最后总结"],
            "style": "简洁、结构化、易读",
            "seo_keywords": ["推荐", "排名", "合集", "盘点", "必备"],
        },
        "story": {
            "structure": ["标题(故事型)", "场景切入", "冲突/转折", "解决方案", "经验提炼"],
            "style": "叙事性强、有代入感",
            "seo_keywords": ["经验", "复盘", "故事", "经历", "教训"],
        },
    }

    PLATFORM_STYLES = {
        "zhihu": {"tone": "专业思辨", "length": "中长篇", "format": "rich_text"},
        "csdn": {"tone": "技术干货", "length": "长篇", "format": "text+code"},
        "toutiao": {"tone": "通俗易懂", "length": "中短篇", "format": "text+image"},
        "xiaohongshu": {"tone": "轻松口语化", "length": "短篇", "format": "text+image+emoji"},
        "wechat_mp": {"tone": "正式深度", "length": "长篇", "format": "rich_text"},
    }

    def __init__(self, config=None):
        self.config = config
        self.results: List[ExecutionResult] = []

    def execute_step(self, step: Dict[str, Any], context: Optional[Dict] = None) -> ExecutionResult:
        """执行单个步骤"""
        action = step.get("action", "")
        logger.info(f"[Executor] 执行步骤: {action}")

        action_map = {
            "research_topic": self._research_topic,
            "generate_outline": self._generate_outline,
            "generate_content": self._generate_content,
            "format_content": self._format_content,
            "analyze_performance": self._analyze_performance,
            "identify_gaps": self._identify_gaps,
            "apply_optimization": self._apply_optimization,
            "prepare_versions": self._prepare_versions,
            "create_variants": self._create_variants,
            "research": self._research_topic,
            "generate": self._generate_content,
        }

        handler = action_map.get(action, self._default_execute)
        try:
            output = handler(step, context or {})
            result = ExecutionResult(step_action=action, success=True, output=output)
        except Exception as e:
            logger.error(f"[Executor] 步骤 {action} 执行失败: {e}")
            result = ExecutionResult(step_action=action, success=False, output=str(e), metadata={"error": str(e)})

        self.results.append(result)
        return result

    def _research_topic(self, step: Dict, context: Dict) -> Dict:
        """话题调研：分析热度、竞争度、切入点"""
        topic = context.get("topic", {}).get("keyword", step.get("config", {}).get("goal", "通用话题"))
        hot_score = context.get("topic", {}).get("hot_score", random.randint(60, 95))
        return {
            "topic": topic,
            "hot_score": hot_score,
            "competition": "中" if hot_score > 80 else "低",
            "recommended_angle": f"从实战角度深入解析{topic}的核心原理与应用",
            "estimated_traffic": hot_score * 100,
            "keywords": [topic, f"{topic}教程", f"{topic}实战", f"{topic}详解"],
            "content_type": random.choice(["tutorial", "insight"]),
        }

    def _generate_outline(self, step: Dict, context: Dict) -> Dict:
        """生成内容大纲"""
        research = context.get("research", {})
        topic = research.get("topic", "通用话题")
        content_type = research.get("content_type", "tutorial")

        if content_type in self.CONTENT_TEMPLATES:
            template = self.CONTENT_TEMPLATES[content_type]
            outline = []
            for i, item in enumerate(template["structure"]):
                item_clean = item.replace("{steps}", "3-5部").replace("{code_blocks}", "2-3个")
                outline.append({
                    "section": i + 1,
                    "title": item_clean,
                    "word_count": random.randint(300, 800),
                    "key_points": [research.get("recommended_angle", topic)],
                })
            return {
                "topic": topic,
                "type": content_type,
                "outline": outline,
                "total_sections": len(outline),
                "estimated_words": sum(o["word_count"] for o in outline),
            }

        return {"topic": topic, "type": "general", "outline": [], "note": "使用通用模板"}

    def _generate_content(self, step: Dict, context: Dict) -> Dict:
        """生成完整内容"""
        topic = context.get("research", {}).get("topic", context.get("topic", "通用主题"))
        outline = context.get("outline", {}).get("outline", [])
        content_type = context.get("outline", {}).get("type", "tutorial")

        paragraphs = []
        title = f"【深度解析】{topic}：从入门到实战全流程指南"

        paragraphs.append(f"## {title}\n")

        intro_templates = [
            f"在当今快速发展的技术环境中，{topic}已经成为不可忽视的关键领域。",
            f"你是否也在寻找关于{topic}的系统性解决方案？本文将为你提供完整指南。",
        ]
        paragraphs.append(random.choice(intro_templates) + "\n")

        for section in outline:
            section_title = section.get("title", f"第{section.get('section', 1)}部分")
            paragraphs.append(f"### {section_title}\n")
            paragraphs.append(
                f"关于{section_title}的详细展开，我们从核心原理出发，结合实战案例，"
                f"深入分析其中的关键要点。通过实际示例代码和操作步骤，帮助读者快速掌握。\n"
            )

            if "代码" in section_title or "code" in section_title.lower():
                paragraphs.append("```python\n# {topic} 示例代码\ndef main():\n    print('Hello {topic}')\n```\n".replace("{topic}", topic))

        paragraphs.append("\n## 总结\n")
        paragraphs.append(f"掌握{topic}的核心技巧，关键在于实践与持续优化。希望本文能为你提供有价值的参考。\n")

        content_body = "\n".join(paragraphs)
        return {
            "title": title,
            "content": content_body,
            "word_count": len(content_body),
            "type": content_type,
            "generated_at": datetime.now().isoformat(),
        }

    def _format_content(self, step: Dict, context: Dict) -> Dict:
        """格式化内容适配不同平台"""
        content = context.get("content", {})
        platform = context.get("platform", "general")
        platform_style = self.PLATFORM_STYLES.get(platform, {"tone": "通用", "format": "text"})
        original = content.get("content", "")

        formatted = {
            "zhihu": f"# {content.get('title', '')}\n\n{original}\n\n> 欢迎点赞、收藏、评论交流~\n\n#深度思考 #{platform}",
            "csdn": f"> 本文已收录于专栏，持续更新中\n\n{original}\n\n---\n*原创不易，转载请注明出处*",
            "xiaohongshu": f"✨{content.get('title', '')}✨\n\n{original[:500]}...\n\n#干货分享 #学习 #{content.get('title', '')[:20]}",
            "toutiao": f"【{content.get('title', '')}】\n\n{original}\n\n#科技 #干货",
            "wechat_mp": f"{original}\n\n---\n关注公众号，获取更多精彩内容",
        }

        result = formatted.get(platform, original)
        return {"platform": platform, "formatted_content": result, "style": platform_style}

    def _analyze_performance(self, step: Dict, context: Dict) -> Dict:
        return {
            "exposure": random.randint(1000, 50000),
            "clicks": random.randint(50, 5000),
            "conversion_rate": round(random.uniform(0.01, 0.15), 3),
            "engagement_score": round(random.uniform(0.3, 0.9), 2),
        }

    def _identify_gaps(self, step: Dict, context: Dict) -> Dict:
        return {
            "gaps": ["标题吸引力不足", "内容深度不够", "SEO关键词密度低"],
            "suggestions": ["增加数据支撑", "优化标题", "增加长尾关键词"],
        }

    def _apply_optimization(self, step: Dict, context: Dict) -> Dict:
        return {"optimized": True, "changes": ["标题优化", "增加数据引用", "SEO关键词扩展"]}

    def _prepare_versions(self, step: Dict, context: Dict) -> Dict:
        platform = context.get("platform", "zhihu")
        return {"version": f"v_{platform}_1", "platform": platform, "status": "ready"}

    def _create_variants(self, step: Dict, context: Dict) -> Dict:
        return {
            "variant_a": {"title_style": "疑问型", "content_length": "medium"},
            "variant_b": {"title_style": "数字型", "content_length": "long"},
            "traffic_split": "50/50",
        }

    def _default_execute(self, step: Dict, context: Dict) -> Dict:
        return {"action": step.get("action"), "result": "executed", "context_keys": list(context.keys())}
