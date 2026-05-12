import json
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("geo.abtest")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class ABTest:
    id: str
    name: str
    hypothesis: str
    variants: List[Dict]
    metrics: Dict[str, List[float]] = field(default_factory=dict)
    status: str = "running"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    concluded_at: Optional[str] = None
    winner: Optional[str] = None


class ABTestEngine:
    """A/B 测试引擎"""

    TEST_DIMENSIONS = [
        "title_style",
        "content_length",
        "publish_time",
        "image_count",
        "cta_style",
        "tone_of_voice",
        "keyword_density",
        "structure_format",
    ]

    TEST_TEMPLATES = {
        "title_style": {
            "variants": [
                {"name": "A_question", "description": "疑问型标题", "example": "为什么你的内容没人看？"},
                {"name": "B_number", "description": "数字型标题", "example": "让内容曝光提升300%的5个方法"},
            ],
            "metric": "ctr",
        },
        "content_length": {
            "variants": [
                {"name": "A_short", "description": "短内容 (500-800字)", "param": {"min_words": 500, "max_words": 800}},
                {"name": "B_long", "description": "长内容 (2000-3000字)", "param": {"min_words": 2000, "max_words": 3000}},
            ],
            "metric": "completion_rate",
        },
        "publish_time": {
            "variants": [
                {"name": "A_morning", "description": "上午发布 (9:00-11:00)", "param": {"hours": [9, 10, 11]}},
                {"name": "B_evening", "description": "晚上发布 (19:00-21:00)", "param": {"hours": [19, 20, 21]}},
            ],
            "metric": "ctr",
        },
        "tone_of_voice": {
            "variants": [
                {"name": "A_professional", "description": "正式专业风格"},
                {"name": "B_casual", "description": "轻松口语风格"},
            ],
            "metric": "engagement_rate",
        },
        "cta_style": {
            "variants": [
                {"name": "A_direct", "description": "直接引导 (关注我了解更多)"},
                {"name": "B_question", "description": "提问引导 (你怎么看？评论区聊聊)"},
            ],
            "metric": "conversion_rate",
        },
    }

    def __init__(self, config=None):
        self.config = config
        self.active_tests: List[ABTest] = []
        self.completed_tests: List[ABTest] = []

    def create_test(self, dimension: str, hypothesis: Optional[str] = None, custom_variants: Optional[List[Dict]] = None) -> ABTest:
        """创建新的 A/B 测试"""
        if dimension not in self.TEST_DIMENSIONS and dimension not in self.TEST_TEMPLATES:
            logger.error(f"[ABTest] 未知测试维度: {dimension}")
            raise ValueError(f"Unknown dimension: {dimension}")

        template = self.TEST_TEMPLATES.get(dimension)
        if not template:
            template = {"variants": [{"name": "A", "description": "对照组"}, {"name": "B", "description": "实验组"}], "metric": "ctr"}

        variants = custom_variants or template["variants"]
        test = ABTest(
            id=f"abtest_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=f"{dimension}_test",
            hypothesis=hypothesis or f"测试 {dimension} 对 {template['metric']} 的影响",
            variants=variants,
            metrics={v["name"]: [] for v in variants},
        )

        self.active_tests.append(test)
        logger.info(f"[ABTest] 创建测试: {test.id} ({dimension})")
        return test

    def create_content_pair(self, base_content: Dict, dimension: str) -> Tuple[Dict, Dict]:
        """为 A/B 测试创建一对内容变体"""
        if dimension not in self.TEST_TEMPLATES:
            return base_content, base_content

        template = self.TEST_TEMPLATES[dimension]
        variant_a = dict(base_content)
        variant_b = dict(base_content)

        variant_a["ab_variant"] = "A"
        variant_a["title"] = template["variants"][0].get("example", base_content.get("title", ""))

        variant_b["ab_variant"] = "B"
        variant_b["title"] = template["variants"][1].get("example", base_content.get("title", ""))

        return variant_a, variant_b

    def record_result(self, test_id: str, variant_name: str, metric_value: float):
        """记录测试结果"""
        for test in self.active_tests:
            if test.id == test_id:
                if variant_name in test.metrics:
                    test.metrics[variant_name].append(metric_value)
                    logger.info(f"[ABTest] 记录: {test_id}[{variant_name}] = {metric_value}")
                return

        for test in self.completed_tests:
            if test.id == test_id:
                if variant_name in test.metrics:
                    test.metrics[variant_name].append(metric_value)
                return

    def simulate_results(self, test_id: str, n_samples: int = 50):
        """模拟收集测试数据"""
        for test in self.active_tests:
            if test.id == test_id:
                base_ctr = random.uniform(0.03, 0.08)
                for v in test.variants:
                    variant_name = v["name"]
                    if variant_name not in test.metrics:
                        test.metrics[variant_name] = []
                    for _ in range(n_samples):
                        noise = random.uniform(-0.02, 0.03)
                        test.metrics[variant_name].append(max(0.001, base_ctr + noise))
                logger.info(f"[ABTest] 模拟数据: {test_id} ({n_samples} 样本/变体)")

    def conclude_test(self, test_id: str) -> Optional[Dict]:
        """结束测试并分析结果"""
        test = None
        for t in self.active_tests:
            if t.id == test_id:
                test = t
                break

        if not test:
            logger.error(f"[ABTest] 未找到测试: {test_id}")
            return None

        analysis = self._analyze_results(test)

        test.status = "completed"
        test.concluded_at = datetime.now().isoformat()
        test.winner = analysis.get("winner")

        self.active_tests = [t for t in self.active_tests if t.id != test_id]
        self.completed_tests.append(test)

        self._save_test_result(test, analysis)
        logger.info(f"[ABTest] 测试结束: {test_id}, 胜出: {test.winner}")
        return analysis

    def _analyze_results(self, test: ABTest) -> Dict:
        """分析 A/B 测试结果"""
        if not test.metrics:
            return {"winner": None, "confidence": 0, "reason": "无数据"}

        variant_stats = {}
        for variant_name, values in test.metrics.items():
            if values:
                avg = sum(values) / len(values)
                variance = sum((v - avg) ** 2 for v in values) / len(values) if len(values) > 1 else 0
                variant_stats[variant_name] = {
                    "mean": round(avg, 5),
                    "std": round(variance ** 0.5, 5),
                    "n": len(values),
                }

        if len(variant_stats) < 2:
            return {"winner": list(variant_stats.keys())[0] if variant_stats else None, "confidence": 0}

        best = max(variant_stats.items(), key=lambda x: x[1]["mean"])
        worst = min(variant_stats.items(), key=lambda x: x[1]["mean"])

        total_n = sum(v["n"] for v in variant_stats.values())
        effect_size = best[1]["mean"] - worst[1]["mean"]
        confidence = min(0.99, max(0.5, 1 - (1 / (1 + effect_size * total_n))))

        return {
            "winner": best[0],
            "variant_stats": variant_stats,
            "effect_size": round(effect_size, 5),
            "confidence": round(confidence, 2),
            "lift_pct": round((effect_size / worst[1]["mean"] * 100), 1) if worst[1]["mean"] > 0 else 0,
            "recommendation": f"推荐采用 {best[0]} 策略，置信度 {confidence:.0%}，提升约 {round((effect_size / worst[1]['mean'] * 100), 1) if worst[1]['mean'] > 0 else 0}%",
        }

    def get_winning_strategies(self) -> List[Dict]:
        """获取所有测试的获胜策略"""
        winners = []
        for test in self.completed_tests:
            if test.winner:
                variant_info = next((v for v in test.variants if v["name"] == test.winner), {})
                winners.append({
                    "dimension": test.name,
                    "winner": test.winner,
                    "description": variant_info.get("description", ""),
                    "hypothesis": test.hypothesis,
                })
        return winners

    def apply_winning_strategies(self) -> Dict[str, Any]:
        """将获胜策略应用到生成系统"""
        strategies = self.get_winning_strategies()
        applied = []

        for s in strategies:
            applied.append({
                "dimension": s["dimension"],
                "new_default": s["description"],
                "source_test": s["winner"],
            })

        return {
            "strategies_applied": len(applied),
            "details": applied,
            "applied_at": datetime.now().isoformat(),
        }

    def _save_test_result(self, test: ABTest, analysis: Dict):
        path = DATA_DIR / "ab_tests" / f"{test.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "id": test.id,
                "name": test.name,
                "hypothesis": test.hypothesis,
                "status": test.status,
                "winner": test.winner,
                "analysis": analysis,
                "concluded_at": test.concluded_at,
            }, f, ensure_ascii=False, indent=2)

    def run_auto_optimization(self, content_generator, n_tests: int = 3) -> Dict:
        """自动运行优化循环：测试 -> 分析 -> 应用"""
        results = []
        dimensions = random.sample(list(self.TEST_TEMPLATES.keys()), min(n_tests, len(self.TEST_TEMPLATES)))

        for dim in dimensions:
            test = self.create_test(dim)
            self.simulate_results(test.id, n_samples=50)
            analysis = self.conclude_test(test.id)
            results.append({"dimension": dim, "analysis": analysis})

        applied = self.apply_winning_strategies()

        return {
            "tests_run": len(results),
            "results": results,
            "strategies_applied": applied,
        }
