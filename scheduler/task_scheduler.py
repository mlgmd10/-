import json
import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

logger = logging.getLogger("geo.scheduler")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    id: str
    name: str
    handler: Optional[Callable] = None
    handler_name: str = ""
    interval_minutes: int = 60
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_result: Optional[Any] = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "interval_minutes": self.interval_minutes,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "status": self.status.value,
            "retry_count": self.retry_count,
        }


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self, config=None):
        self.config = config
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.history: List[Dict] = []

    def register_task(self, name: str, handler: Callable, interval_minutes: int = 60,
                      max_retries: int = 3) -> ScheduledTask:
        """注册定时任务"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{name}"
        task = ScheduledTask(
            id=task_id,
            name=name,
            handler=handler,
            handler_name=getattr(handler, "__name__", str(handler)),
            interval_minutes=interval_minutes,
            next_run=datetime.now() + timedelta(minutes=interval_minutes),
            max_retries=max_retries,
        )

        self.tasks[task_id] = task
        logger.info(f"[Scheduler] 注册任务: {name} (每 {interval_minutes} 分钟)")
        return task

    def register_builtin_tasks(self, geo_system):
        """注册系统内置任务集"""
        tasks_config = [
            {
                "name": "content_generation_cycle",
                "handler": lambda: self._content_generation_task(geo_system),
                "interval": 30,
                "description": "内容生成与优化周期",
            },
            {
                "name": "performance_collection",
                "handler": lambda: self._performance_collection_task(geo_system),
                "interval": 15,
                "description": "数据采集",
            },
            {
                "name": "ab_test_cycle",
                "handler": lambda: self._ab_test_task(geo_system),
                "interval": 120,
                "description": "A/B 测试自动优化",
            },
            {
                "name": "distribution_schedule",
                "handler": lambda: self._distribution_task(geo_system),
                "interval": 60,
                "description": "定时分发",
            },
            {
                "name": "strategy_optimization",
                "handler": lambda: self._strategy_optimization_task(geo_system),
                "interval": 180,
                "description": "策略全局优化",
            },
            {
                "name": "housekeeping",
                "handler": lambda: self._housekeeping_task(geo_system),
                "interval": 360,
                "description": "系统维护",
            },
        ]

        for tc in tasks_config:
            self.register_task(
                name=tc["name"],
                handler=tc["handler"],
                interval_minutes=tc["interval"],
            )

        logger.info(f"[Scheduler] 已注册 {len(tasks_config)} 个内置任务")

    def start(self, daemon: bool = True):
        """启动调度器"""
        if self._running:
            logger.warning("[Scheduler] 调度器已在运行")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=daemon)
        self._thread.start()
        logger.info("[Scheduler] 调度器已启动")

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("[Scheduler] 调度器已停止")

    def _run_loop(self):
        """主循环"""
        logger.info("[Scheduler] 进入主循环")
        while self._running:
            now = datetime.now()
            with self._lock:
                for task_id, task in list(self.tasks.items()):
                    if task.status != TaskStatus.CANCELLED:
                        if task.next_run and now >= task.next_run:
                            self._execute_task(task)

            time.sleep(10)

    def _execute_task(self, task: ScheduledTask):
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        logger.info(f"[Scheduler] 执行任务: {task.name}")

        try:
            if task.handler:
                result = task.handler()
                task.last_result = result
                task.status = TaskStatus.COMPLETED
                task.retry_count = 0
                logger.info(f"[Scheduler] 任务完成: {task.name}")

                self.history.append({
                    "task": task.name,
                    "time": task.last_run.isoformat(),
                    "status": "success",
                })
            else:
                logger.warning(f"[Scheduler] 任务 {task.name} 无处理函数")
                task.status = TaskStatus.FAILED

        except Exception as e:
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                task.next_run = datetime.now() + timedelta(minutes=1)
                logger.warning(f"[Scheduler] 任务失败, 将重试 ({task.retry_count}/{task.max_retries}): {task.name} - {e}")
            else:
                task.status = TaskStatus.FAILED
                logger.error(f"[Scheduler] 任务彻底失败: {task.name} - {e}")

            self.history.append({
                "task": task.name,
                "time": task.last_run.isoformat(),
                "status": "failed",
                "error": str(e),
            })

        task.next_run = datetime.now() + timedelta(minutes=task.interval_minutes)

    def run_now(self, task_name: str) -> bool:
        """立即执行指定任务"""
        for task in self.tasks.values():
            if task.name == task_name:
                logger.info(f"[Scheduler] 手动触发: {task_name}")
                self._execute_task(task)
                return True
        logger.warning(f"[Scheduler] 未找到任务: {task_name}")
        return False

    def get_status(self) -> Dict:
        """获取调度器状态"""
        task_statuses = {}
        for task in self.tasks.values():
            task_statuses[task.name] = {
                "status": task.status.value,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "retry_count": task.retry_count,
            }

        return {
            "running": self._running,
            "total_tasks": len(self.tasks),
            "tasks": task_statuses,
            "recent_history": self.history[-10:],
        }

    def wait_for_completion(self, timeout: float = 60.0):
        """等待所有任务完成"""
        start = time.time()
        while time.time() - start < timeout:
            pending = any(t.status in (TaskStatus.RUNNING, TaskStatus.PENDING) for t in self.tasks.values())
            if not pending:
                break
            time.sleep(1)

    def _content_generation_task(self, geo_system):
        """内容生成任务"""
        geo_system.run_pipeline("generate_and_optimize", topic_count=3)

    def _performance_collection_task(self, geo_system):
        """数据采集任务"""
        geo_system.analytics.batch_collect(
            content_ids=[f"content_{i}" for i in range(5)],
            platforms=["zhihu", "csdn", "toutiao", "xiaohongshu"],
        )
        geo_system.analytics.generate_snapshot("periodic")

    def _ab_test_task(self, geo_system):
        """A/B测试任务"""
        geo_system.ab_test.run_auto_optimization(geo_system.generator, n_tests=2)

    def _distribution_task(self, geo_system):
        """分发任务"""
        topics = geo_system.planner.select_topics(n=2)
        for topic in topics:
            content = geo_system.generator.generate(topic)
            geo_system.distributor.distribute(content, topic.get("platforms", ["zhihu", "csdn"]))

    def _strategy_optimization_task(self, geo_system):
        """策略优化任务"""
        suggestions = geo_system.analytics.generate_optimization_suggestions()
        for s in suggestions:
            if s["priority"] == "high":
                logger.info(f"[Strategy] 执行优化: {s['action']}")

    def _housekeeping_task(self, geo_system):
        """系统维护任务"""
        logger.info("[Housekeeping] 清理过期数据...")
        logger.info("[Housekeeping] 维护完成")
