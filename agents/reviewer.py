import json
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("geo.reviewer")


@dataclass
class ReviewResult:
    step_action: str
    score: float
    passed: bool
    feedback: str
    suggestions: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "step_action": self.step_action,
            "score": self.score,
            "passed": self.passed,
            "feedback": self.feedback,
            "suggestions": self.suggestions,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class ReviewerAgent:
    """质量评估与策略修正 Agent"""

    QUALITY_DIMENSIONS = [
        "originality",
        "depth",
        "readability",
        "seo_friendliness",
        "platform_fit",
        "engagement_potential",
    ]

    REVIEW_RULES = {
        "originality": {
            "weight": 0.20,
            "check": "内容是否具有独特观点或新信息",
            "max_score": 10,
        },
        "depth": {
            "weight": 0.25,
            "check": "分析深度是否充分，是否覆盖核心要点",
            "max_score": 10,
        },
        "readability": {
            "weight": 0.15,
            "check": "结构清晰度、语言流畅度",
            "max_score": 10,
        },
        "seo_friendliness": {
            "weight": 0.20,
            "check": "关键词密度、标题优化、标签使用",
            "max_score": 10,
        },
        "platform_fit": {
            "weight": 0.10,
            "check": "内容风格与目标平台匹配度",
            "max_score": 10,
        },
        "engagement_potential": {
            "weight": 0.10,
            "check": "引发互动(评论/分享/收藏)的潜力",
            "max_score": 10,
        },
    }

    def __init__(self, config=None):
        self.config = config
        self.review_history: List[ReviewResult] = []
        self.min_pass_score = getattr(config, "min_quality_score", 0.7) if config else 0.7

    def review(self, step: Dict, execution_result: Any, context: Optional[Dict] = None) -> ReviewResult:
        """对执行结果进行多维度质量评估"""
        action = step.get("action", "unknown")
        logger.info(f"[Reviewer] 审核步骤: {action}")

        scores = {}
        feedback_items = []
        suggestions = []

        for dim in self.QUALITY_DIMENSIONS:
            rule = self.REVIEW_RULES[dim]
            score = self._score_dimension(dim, execution_result, context or {})
            scores[dim] = {"score": score, "max": rule["max_score"], "check": rule["check"]}

            if score < 6:
                suggestions.append(f"[{dim}] {self._get_suggestion(dim)}")
                feedback_items.append(f"{dim}: 不合格 ({score}/10) - {rule['check']}")
            elif score < 8:
                feedback_items.append(f"{dim}: 良好 ({score}/10)")

        weighted_score = sum(
            scores[d]["score"] / scores[d]["max"] * self.REVIEW_RULES[d]["weight"]
            for d in self.QUALITY_DIMENSIONS
        )
        normalized_score = round(weighted_score / sum(r["weight"] for r in self.REVIEW_RULES.values()), 3)

        passed = normalized_score >= self.min_pass_score
        feedback = "; ".join(feedback_items) if feedback_items else f"整体质量优秀 ({normalized_score})"

        result = ReviewResult(
            step_action=action,
            score=normalized_score,
            passed=passed,
            feedback=feedback,
            suggestions=suggestions,
            metadata={"dimension_scores": scores, "threshold": self.min_pass_score},
        )

        self.review_history.append(result)
        return result

    def _score_dimension(self, dim: str, execution_result: Any, context: Dict) -> float:
        """对单个维度打分 (0-10)"""
        base = 5.0
        if hasattr(execution_result, "output"):
            output = execution_result.output
            if isinstance(output, dict):
                content_len = len(str(output))
                base += min(content_len / 500, 3)
                if output.get("title"):
                    base += 1
                if output.get("keywords"):
                    base += 0.5
            elif isinstance(output, str):
                base += min(len(output) / 300, 2)
            else:
                base += 1

        if dim == "seo_friendliness":
            base = max(base, 5.0)
        elif dim == "originality":
            base = max(base - 0.5, 2.0)
        elif dim == "readability":
            base = max(base, 4.0)

        return round(min(base + random.uniform(-1, 1.5), 10), 1)

    def _get_suggestion(self, dim: str) -> str:
        suggestions_map = {
            "originality": "增加独特观点或最新数据，避免泛泛而谈",
            "depth": "补充更深层的原理分析和更多实战案例",
            "readability": "优化段落结构，增加小标题和列表形式",
            "seo_friendliness": "增加长尾关键词，优化标题和标签",
            "platform_fit": "调整语气和内容长度以适配目标平台风格",
            "engagement_potential": "添加互动引导、问题讨论或投票",
        }
        return suggestions_map.get(dim, "需要进一步优化")

    def get_optimization_strategy(self, review: ReviewResult) -> Dict:
        """基于审核结果生成优化策略"""
        priority_suggestions = sorted(
            review.suggestions,
            key=lambda s: self.REVIEW_RULES.get(s.split("]")[0].strip("["), {}).get("weight", 0),
            reverse=True,
        )

        return {
            "content_score": review.score,
            "priority_fixes": priority_suggestions[:3],
            "require_regeneration": review.score < 0.5,
            "recommended_prompts": self._generate_improved_prompts(review),
            "iteration_recommended": review.score < 0.8,
        }

    def _generate_improved_prompts(self, review: ReviewResult) -> List[str]:
        """根据审核反馈生成改进后的 Prompt"""
        prompts = []
        for s in review.suggestions:
            if "originality" in s and "独特" in s:
                prompts.append("请在此内容中融入你独有的技术洞察和真实项目经验")
            elif "depth" in s:
                prompts.append("请增加2-3个真实案例，并对每个技术点做深度解析")
            elif "seo" in s:
                prompts.append("在标题和首段中自然融入核心关键词，并在文末附上3-5个相关标签")
            elif "readability" in s:
                prompts.append("请使用更清晰的层级结构，每个大段落配一个小标题")
        return prompts

    def compare_variants(self, variant_results: List[Dict]) -> Dict:
        """比较 A/B 测试变体效果"""
        if not variant_results:
            return {"winner": None, "confidence": 0}

        best = max(variant_results, key=lambda v: (
            v.get("exposure", 0) * 0.1 + v.get("clicks", 0) * 1.0 + v.get("conversion_rate", 0) * 100
        ))

        return {
            "winner": best.get("variant_name", "unknown"),
            "metrics": best,
            "recommendation": {
                "adopt": best.get("title_style", ""),
                "performance_diff": f"曝光: {best.get('exposure', 0)}, 点击: {best.get('clicks', 0)}",
            },
        }
