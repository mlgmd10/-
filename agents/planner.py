import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("geo.planner")


@dataclass
class TaskPlan:
    id: str
    goal: str
    steps: List[Dict[str, Any]]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"
    priority: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": self.steps,
            "created_at": self.created_at,
            "status": self.status,
            "priority": self.priority,
        }


class PlannerAgent:
    """目标拆解与路径规划 Agent"""

    STEP_TEMPLATES = {
        "content_creation": {
            "type": "content_creation",
            "description": "生成内容",
            "sub_steps": [
                {"action": "research_topic", "desc": "调研话题热度和切入点"},
                {"action": "generate_outline", "desc": "生成内容大纲"},
                {"action": "generate_content", "desc": "基于大纲生成完整内容"},
                {"action": "format_content", "desc": "格式化内容适配不同平台"},
            ],
        },
        "content_optimization": {
            "type": "content_optimization",
            "description": "优化已有内容",
            "sub_steps": [
                {"action": "analyze_performance", "desc": "分析现有内容表现数据"},
                {"action": "identify_gaps", "desc": "识别优化空间"},
                {"action": "apply_optimization", "desc": "应用优化策略"},
                {"action": "validate_quality", "desc": "验证优化效果"},
            ],
        },
        "distribution": {
            "type": "distribution",
            "description": "内容分发",
            "sub_steps": [
                {"action": "prepare_versions", "desc": "准备各平台适配版本"},
                {"action": "schedule_posts", "desc": "安排发布时间"},
                {"action": "publish", "desc": "执行发布"},
                {"action": "verify_publish", "desc": "验证发布结果"},
            ],
        },
        "ab_test": {
            "type": "ab_test",
            "description": "A/B 测试",
            "sub_steps": [
                {"action": "create_variants", "desc": "创建内容变体"},
                {"action": "distribute_variants", "desc": "分发不同变体"},
                {"action": "collect_data", "desc": "收集测试数据"},
                {"action": "analyze_results", "desc": "分析结果并决策"},
            ],
        },
    }

    def __init__(self, config=None):
        self.config = config
        self.plans: List[TaskPlan] = []
        self.topics_db: List[Dict] = []
        self._load_topics()

    def _load_topics(self):
        topics = [
            {"keyword": "AI自动化", "hot_score": 95, "category": "技术", "platforms": ["zhihu", "csdn"]},
            {"keyword": "Python开发", "hot_score": 90, "category": "技术", "platforms": ["csdn", "toutiao"]},
            {"keyword": "内容创作", "hot_score": 88, "category": "自媒体", "platforms": ["xiaohongshu", "zhihu"]},
            {"keyword": "SEO优化", "hot_score": 85, "category": "营销", "platforms": ["csdn", "zhihu"]},
            {"keyword": "多Agent系统", "hot_score": 80, "category": "技术", "platforms": ["zhihu", "csdn"]},
            {"keyword": "数据驱动", "hot_score": 78, "category": "技术", "platforms": ["toutiao", "csdn"]},
            {"keyword": "自动化发布", "hot_score": 76, "category": "技术", "platforms": ["csdn", "zhihu"]},
            {"keyword": "增长黑客", "hot_score": 82, "category": "营销", "platforms": ["zhihu", "xiaohongshu"]},
        ]
        self.topics_db = topics

    def decompose_goal(self, goal: str) -> TaskPlan:
        """将高层目标拆解为可执行的步骤列表"""
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        steps = []

        goal_lower = goal.lower()

        if any(k in goal_lower for k in ["生成", "创建", "写", "create", "generate"]):
            steps = self._plan_content_creation(goal)
        elif any(k in goal_lower for k in ["优化", "改进", "optimize", "improve"]):
            steps = self._plan_optimization(goal)
        elif any(k in goal_lower for k in ["发布", "分发", "publish", "distribute"]):
            steps = self._plan_distribution(goal)
        elif any(k in goal_lower for k in ["测试", "ab", "test"]):
            steps = self._plan_ab_test(goal)
        else:
            steps = self._plan_default(goal)

        plan = TaskPlan(id=plan_id, goal=goal, steps=steps)
        self.plans.append(plan)
        logger.info(f"[Planner] 已创建计划: {plan_id} -> {goal} ({len(steps)} 步)")
        return plan

    def select_topics(self, n: int = 3, category: Optional[str] = None) -> List[Dict]:
        """根据热度选择高价值话题"""
        candidates = self.topics_db
        if category:
            candidates = [t for t in candidates if t["category"] == category]
        candidates.sort(key=lambda x: x["hot_score"], reverse=True)
        selected = candidates[:n]
        logger.info(f"[Planner] 已选择 {len(selected)} 个话题")
        return selected

    def _plan_content_creation(self, goal: str) -> List[Dict]:
        template = self.STEP_TEMPLATES["content_creation"]
        steps = []
        for s in template["sub_steps"]:
            steps.append({
                "action": s["action"],
                "description": s["desc"],
                "status": "pending",
                "dependencies": [],
                "config": {"goal": goal, "template_type": template["type"]},
                "assigned_to": "executor",
            })
        steps[-1]["assigned_to"] = "reviewer"
        return steps

    def _plan_optimization(self, goal: str) -> List[Dict]:
        template = self.STEP_TEMPLATES["content_optimization"]
        steps = []
        for i, s in enumerate(template["sub_steps"]):
            steps.append({
                "action": s["action"],
                "description": s["desc"],
                "status": "pending",
                "dependencies": ["analyze_performance"] if s["action"] != "analyze_performance" else [],
                "config": {"goal": goal, "template_type": template["type"]},
                "assigned_to": "executor" if i < 3 else "reviewer",
            })
        return steps

    def _plan_distribution(self, goal: str) -> List[Dict]:
        template = self.STEP_TEMPLATES["distribution"]
        steps = []
        for i, s in enumerate(template["sub_steps"]):
            steps.append({
                "action": s["action"],
                "description": s["desc"],
                "status": "pending",
                "dependencies": ["prepare_versions"] if s["action"] != "prepare_versions" else [],
                "config": {"goal": goal, "template_type": template["type"]},
                "assigned_to": "executor" if i < 3 else "reviewer",
            })
        return steps

    def _plan_ab_test(self, goal: str) -> List[Dict]:
        template = self.STEP_TEMPLATES["ab_test"]
        steps = []
        for i, s in enumerate(template["sub_steps"]):
            steps.append({
                "action": s["action"],
                "description": s["desc"],
                "status": "pending",
                "dependencies": ["create_variants"] if s["action"] != "create_variants" else [],
                "config": {"goal": goal, "template_type": template["type"], "variant_count": 2},
                "assigned_to": "executor" if i < 2 else "reviewer",
            })
        return steps

    def _plan_default(self, goal: str) -> List[Dict]:
        return [
            {
                "action": "research",
                "description": f"调研: {goal}",
                "status": "pending",
                "dependencies": [],
                "config": {"goal": goal},
                "assigned_to": "executor",
            },
            {
                "action": "generate",
                "description": f"生成内容: {goal}",
                "status": "pending",
                "dependencies": ["research"],
                "config": {"goal": goal},
                "assigned_to": "executor",
            },
            {
                "action": "review",
                "description": f"审核内容: {goal}",
                "status": "pending",
                "dependencies": ["generate"],
                "config": {"goal": goal},
                "assigned_to": "reviewer",
            },
        ]

    def get_plan(self, plan_id: str) -> Optional[TaskPlan]:
        for p in self.plans:
            if p.id == plan_id:
                return p
        return None

    def get_next_step(self, plan_id: str) -> Optional[Dict]:
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        for step in plan.steps:
            if step["status"] == "pending":
                deps_ready = all(
                    any(s["action"] == d and s["status"] == "completed" for s in plan.steps)
                    for d in step["dependencies"]
                )
                if deps_ready:
                    return step
        return None
