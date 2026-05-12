import json
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("geo.optimizer")


class ContentOptimizer:
    """内容优化引擎：SEO优化、可读性提升、平台适配调整"""

    SEO_STRATEGIES = {
        "title_optimization": {
            "techniques": [
                "数字标题 (如'5个方法...')",
                "疑问句式 (如'为什么...？')",
                "紧迫感 (如'现在就开始...')",
                "价值前置 (如'提升效率300%的方法')",
            ],
            "impact_score": 0.9,
        },
        "keyword_density": {
            "optimal_density": (0.02, 0.05),
            "placement": ["标题", "首段", "H2标签", "末段", "Alt标签"],
            "impact_score": 0.75,
        },
        "structure": {
            "best_practices": [
                "H1-H6层级清晰",
                "段落不超过4行",
                "使用列表和引用块",
                "添加目录(长文)",
            ],
            "impact_score": 0.65,
        },
        "readability": {
            "techniques": [
                "短句优先",
                "主动语态",
                "专业术语有注释",
                "图表辅助说明",
            ],
            "impact_score": 0.7,
        },
        "engagement": {
            "techniques": [
                "文末互动引导",
                "内链交叉引用",
                "评论区问题预设",
                "收藏引导语",
            ],
            "impact_score": 0.6,
        },
    }

    def __init__(self, config=None):
        self.config = config
        self.optimization_history: List[Dict] = []

    def optimize(self, content: Dict, target_score: float = 0.8) -> Dict:
        """对内容进行多策略综合优化"""
        logger.info(f"[Optimizer] 优化内容: {content.get('title', '')[:30]}...")

        original = content.copy()
        optimized = content.copy()
        changes = []

        changes += self._optimize_title(optimized)
        changes += self._optimize_keywords(optimized)
        changes += self._optimize_structure(optimized)
        changes += self._enhance_readability(optimized)
        changes += self._add_engagement_elements(optimized)

        optimized["optimization_changes"] = changes
        optimized["optimized_at"] = datetime.now().isoformat()
        optimized["original_quality"] = original.get("quality_score", 0)
        optimized["optimized_quality"] = min(original.get("quality_score", 0.5) + 0.15, 1.0)
        optimized["status"] = "optimized"

        self.optimization_history.append({
            "content_id": original.get("id", ""),
            "changes": changes,
            "before_score": original.get("quality_score", 0),
            "after_score": optimized["optimized_quality"],
        })

        return optimized

    def _optimize_title(self, content: Dict) -> List[str]:
        title = content.get("title", "")
        changes = []

        if " " in title and len(title) < 15:
            content["title"] = title + " | 完整指南"
            changes.append("title: 添加后缀增强描述")

        for kw in content.get("seo_keywords", []):
            if kw and kw not in title:
                if len(title) + len(kw) < 80:
                    content["title"] = title.replace("|", f"| {kw}")
                    changes.append(f"title: 融入关键词 '{kw}'")
                break

        return changes

    def _optimize_keywords(self, content: Dict) -> List[str]:
        body = content.get("body", "")
        keywords = content.get("seo_keywords", [])
        changes = []

        for kw in keywords:
            if kw and kw not in body:
                position = body.find("##") + 2 if "##" in body else 0
                snippet = f" 在{kw}领域，"
                content["body"] = body[:position] + snippet + body[position:]
                changes.append(f"keywords: 植入 '{kw}'")
                break

        return changes

    def _optimize_structure(self, content: Dict) -> List[str]:
        body = content.get("body", "")
        changes = []

        h2_count = body.count("## ")
        if h2_count < 2:
            content["body"] = "## 概述\n\n" + body + "\n\n## 总结\n\n"
            changes.append("structure: 添加章节结构")
        elif h2_count > 5:
            pass

        return changes

    def _enhance_readability(self, content: Dict) -> List[str]:
        body = content.get("body", "")
        changes = []

        long_paragraphs = [p for p in body.split("\n\n") if len(p) > 300]
        if long_paragraphs:
            changes.append("readability: 建议缩短长段落")

        return changes

    def _add_engagement_elements(self, content: Dict) -> List[str]:
        body = content.get("body", "")
        changes = []

        if "?" not in body[-200:]:
            content["body"] = body + "\n\n---\n> 💡 你有什么想法？欢迎在评论区交流讨论！"
            changes.append("engagement: 添加互动引导")

        return changes

    def optimize_for_platform(self, content: Dict, platform: str) -> Dict:
        """针对特定平台优化内容"""
        platform_configs = {
            "zhihu": {
                "title_style": "观点鲜明",
                "tone": "专业思辨",
                "structure_addons": ["开头用提问引发思考", "分点论证", "文末升华观点"],
                "max_length": 10000,
                "tags": ["#数据", "#分析", "#趋势"],
            },
            "csdn": {
                "title_style": "技术明确",
                "tone": "专业干货",
                "structure_addons": ["目录导航", "代码块", "参考文献"],
                "max_length": 20000,
                "tags": ["#技术", "#教程", "#原创"],
            },
            "xiaohongshu": {
                "title_style": "有趣吸睛",
                "tone": "轻松口语化",
                "structure_addons": ["emoji装饰", "短句分行", "视觉符号"],
                "max_length": 1000,
                "tags": ["#干货分享", "#学习打卡", "#效率提升"],
            },
            "toutiao": {
                "title_style": "通俗吸睛",
                "tone": "通俗易懂",
                "structure_addons": ["热点关联", "多图配文", "互动提问"],
                "max_length": 5000,
                "tags": ["#科技", "#干货", "#效率"],
            },
            "wechat_mp": {
                "title_style": "深度正式",
                "tone": "正式专业",
                "structure_addons": ["引导关注", "卡片样式", "图片来源"],
                "max_length": 20000,
                "tags": [],
            },
        }

        config = platform_configs.get(platform, {"tone": "通用", "max_length": 5000})
        optimized = content.copy()
        optimized["platform"] = platform
        optimized["platform_config"] = config
        optimized["formatted_at"] = datetime.now().isoformat()

        body = optimized.get("body", "")
        if len(body) > config.get("max_length", 5000):
            optimized["body"] = body[:config["max_length"]] + "\n\n... (内容已按平台要求截断)"

        return optimized
