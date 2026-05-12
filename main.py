import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

from agents.planner import PlannerAgent, TaskPlan
from agents.executor import ExecutorAgent, ExecutionResult
from agents.reviewer import ReviewerAgent, ReviewResult
from geo.content_generator import ContentGenerator, ContentPiece
from geo.optimizer import ContentOptimizer
from geo.distributor import ContentDistributor
from geo.analytics import AnalyticsEngine
from geo.ab_test import ABTestEngine
from scheduler.task_scheduler import TaskScheduler
from config.settings import Config, config as default_config

logger = logging.getLogger("geo.system")


@dataclass
class PipelineResult:
    pipeline_id: str
    goal: str
    plan: Optional[TaskPlan] = None
    steps_executed: int = 0
    steps_passed: int = 0
    content_generated: int = 0
    content_distributed: int = 0
    quality_score: float = 0.0
    feedback_rounds: int = 0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    errors: List[str] = field(default_factory=list)


class GEOSystem:
    """GEO 内容分发与优化系统 - 核心编排器"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or default_config
        self.pipeline_history: List[PipelineResult] = []

        self.planner = PlannerAgent(config=self.config.agent)
        self.executor = ExecutorAgent(config=self.config.agent)
        self.reviewer = ReviewerAgent(config=self.config.agent)

        self.generator = ContentGenerator(config=self.config.geo)
        self.optimizer = ContentOptimizer(config=self.config.geo)
        self.distributor = ContentDistributor(config=self.config)
        self.analytics = AnalyticsEngine(config=self.config)
        self.ab_test = ABTestEngine(config=self.config.geo)

        self.scheduler = TaskScheduler(config=self.config.scheduler)

        logger.info("[GEOSystem] 系统初始化完成")

    def run_pipeline(self, goal: str, **kwargs) -> PipelineResult:
        """运行完整的 'Planner -> Executor -> Reviewer' 工作流"""
        pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result = PipelineResult(pipeline_id=pipeline_id, goal=goal)
        logger.info(f"[Pipeline] 启动: {pipeline_id} -> {goal}")

        plan = self.planner.decompose_goal(goal)
        result.plan = plan

        context: Dict[str, Any] = {"goal": goal}
        max_rounds = getattr(self.config.agent, "max_rounds", 5)

        for round_num in range(1, max_rounds + 1):
            logger.info(f"[Pipeline] 第 {round_num}/{max_rounds} 轮")

            for step in plan.steps:
                if step["status"] != "pending":
                    continue

                deps_ready = all(
                    any(s["action"] == d and s["status"] == "completed" for s in plan.steps)
                    for d in step.get("dependencies", [])
                )
                if not deps_ready:
                    continue

                step["status"] = "in_progress"
                step_result = self.executor.execute_step(step, context)
                result.steps_executed += 1

                if step_result.success:
                    context[step["action"]] = step_result.output
                    step["status"] = "completed"
                    step["result"] = step_result.output

                    review = self.reviewer.review(step, step_result, context)
                    if review.passed:
                        step["passed_review"] = True
                        result.steps_passed += 1
                    else:
                        step["passed_review"] = False
                        result.feedback_rounds += 1
                        strategy = self.reviewer.get_optimization_strategy(review)
                        context.setdefault("optimization_strategies", []).append(strategy)

                        if strategy.get("require_regeneration", False):
                            logger.info(f"[Pipeline] 重新生成: {step['action']}")
                            step_result = self.executor.execute_step(step, context)
                            context[step["action"]] = step_result.output
                            result.feedback_rounds += 1
                else:
                    step["status"] = "failed"
                    result.errors.append(f"{step['action']}: {step_result.output}")

                result.quality_score = self._compute_pipeline_score(plan)

            all_done = all(s["status"] in ("completed", "failed") for s in plan.steps)
            if all_done:
                break

        plan.status = "completed"
        result.completed_at = datetime.now().isoformat()
        self.pipeline_history.append(result)

        logger.info(f"[Pipeline] 完成: {pipeline_id} | 步骤: {result.steps_executed}/{len(plan.steps)} "
                    f"| 评审通过: {result.steps_passed} | 评分: {result.quality_score:.2f}")
        return result

    def generate_and_optimize(self, topic_count: int = 3, auto_distribute: bool = True) -> Dict:
        """生成并优化内容"""
        topics = self.planner.select_topics(n=topic_count)
        generated = []

        for topic in topics:
            content = self.generator.generate(topic)
            content_dict = content.to_dict()

            optimized = self.optimizer.optimize(content_dict)
            generated.append(optimized)

        result = {
            "topics_selected": len(topics),
            "content_generated": len(generated),
            "average_quality": sum(c.get("optimized_quality", 0) for c in generated) / len(generated) if generated else 0,
            "contents": generated,
        }

        if auto_distribute:
            dist_results = []
            for c in generated:
                platforms = c.get("target_platforms", list(self.distributor.PLATFORM_SPECS.keys()))
                records = self.distributor.distribute(c, platforms)
                dist_results.extend(records)
            result["distributions"] = len(dist_results)
            result["distribution_success"] = sum(1 for r in dist_results if r.status == "published")

        return result

    def run_ab_test_cycle(self, dimension: Optional[str] = None) -> Dict:
        """运行 A/B 测试周期"""
        if dimension:
            test = self.ab_test.create_test(dimension)
            self.ab_test.simulate_results(test.id, n_samples=50)
            analysis = self.ab_test.conclude_test(test.id)
            return {"dimension": dimension, "test_id": test.id, "analysis": analysis}
        else:
            return self.ab_test.run_auto_optimization(self.generator, n_tests=3)

    def collect_and_analyze(self) -> Dict:
        """采集数据并生成分析报告"""
        self.analytics.batch_collect(
            content_ids=[f"content_{i}" for i in range(10)],
        )
        snapshot = self.analytics.generate_snapshot("hourly")
        dashboard = self.analytics.get_dashboard_data()
        return {"snapshot_metrics": snapshot.platform_metrics, "dashboard": dashboard}

    def start_scheduler(self):
        """启动定时调度"""
        self.scheduler.register_builtin_tasks(self)
        self.scheduler.start(daemon=True)
        logger.info("[GEOSystem] 调度器已启动，系统进入持续运行模式")

    def stop_scheduler(self):
        """停止调度"""
        self.scheduler.stop()

    def get_system_status(self) -> Dict:
        """获取系统运行状态"""
        scheduler_status = self.scheduler.get_status()
        dist_stats = self.distributor.get_distribution_stats()

        return {
            "timestamp": datetime.now().isoformat(),
            "scheduler": scheduler_status,
            "distribution": dist_stats,
            "content_generated": len(self.generator.generated),
            "active_ab_tests": len(self.ab_test.active_tests),
            "completed_ab_tests": len(self.ab_test.completed_tests),
            "pipeline_runs": len(self.pipeline_history),
            "analytics_buffer_size": len(self.analytics.realtime_buffer),
        }

    def run_full_cycle(self) -> Dict:
        """运行完整闭环周期：选题 -> 生成 -> 优化 -> 分发 -> 采集 -> 反馈"""
        logger.info("[FullCycle] ====== 开始完整闭环周期 ======")
        cycle_result = {"started_at": datetime.now().isoformat(), "stages": {}}

        pipeline = self.run_pipeline("生成并分发内容")
        cycle_result["stages"]["pipeline"] = {
            "goal": pipeline.goal,
            "steps": pipeline.steps_executed,
            "quality": pipeline.quality_score,
            "feedback_rounds": pipeline.feedback_rounds,
        }

        gen_result = self.generate_and_optimize(topic_count=3, auto_distribute=True)
        cycle_result["stages"]["generation"] = gen_result

        analytics = self.collect_and_analyze()
        cycle_result["stages"]["analytics"] = {
            "total_exposure": analytics["dashboard"].get("total_exposure", 0),
            "avg_ctr": analytics["dashboard"].get("avg_ctr", 0),
            "suggestions": len(analytics["dashboard"].get("optimization_suggestions", [])),
        }

        suggestions = self.analytics.generate_optimization_suggestions()
        for s in suggestions:
            if s["priority"] == "high":
                self.generator.update_prompt_from_feedback(
                    "tutorial", {"ctr": analytics["dashboard"].get("avg_ctr", 0)}
                )

        cycle_result["completed_at"] = datetime.now().isoformat()
        duration = (datetime.now() - datetime.fromisoformat(cycle_result["started_at"])).total_seconds()
        cycle_result["duration_seconds"] = duration

        logger.info(f"[FullCycle] ====== 闭环完成 ({duration:.1f}s) ======")
        return cycle_result

    def _compute_pipeline_score(self, plan: TaskPlan) -> float:
        completed = [s for s in plan.steps if s["status"] == "completed"]
        passed = [s for s in completed if s.get("passed_review", False)]
        if not completed:
            return 0.0
        return len(passed) / len(plan.steps)

    def export_report(self, filepath: str = "output/report.json"):
        """导出运行报告"""
        report = {
            "system_status": self.get_system_status(),
            "content_summary": f"已生成 {len(self.generator.generated)} 条内容",
            "distribution_summary": self.distributor.get_distribution_stats(),
            "pipeline_history": [
                {"id": p.pipeline_id, "goal": p.goal, "score": p.quality_score}
                for p in self.pipeline_history[-5:]
            ],
        }
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"[Report] 报告已导出: {filepath}")
