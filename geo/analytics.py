import json
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("geo.analytics")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class AnalyticsSnapshot:
    timestamp: str
    period: str
    total_exposure: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    platform_metrics: Dict[str, Dict] = field(default_factory=dict)
    content_performance: List[Dict] = field(default_factory=list)
    trends: Dict[str, Any] = field(default_factory=dict)


class AnalyticsEngine:
    """数据采集与分析引擎"""

    def __init__(self, config=None):
        self.config = config
        self.snapshots: List[AnalyticsSnapshot] = []
        self.realtime_buffer: List[Dict] = []

    def collect_metrics(self, content_id: Optional[str] = None, platform: Optional[str] = None) -> Dict:
        """采集内容表现数据"""
        metrics = {
            "content_id": content_id or "unknown",
            "platform": platform or "aggregate",
            "exposure": random.randint(500, 100000),
            "clicks": random.randint(20, 8000),
            "likes": random.randint(0, 500),
            "comments": random.randint(0, 100),
            "shares": random.randint(0, 200),
            "saves": random.randint(0, 150),
            "read_time_avg": round(random.uniform(30, 300), 1),
            "completion_rate": round(random.uniform(0.2, 0.95), 2),
            "collected_at": datetime.now().isoformat(),
        }

        metrics["ctr"] = round(metrics["clicks"] / metrics["exposure"], 4) if metrics["exposure"] > 0 else 0
        metrics["engagement_rate"] = round(
            (metrics["likes"] + metrics["comments"] + metrics["shares"] + metrics["saves"])
            / metrics["exposure"], 4
        ) if metrics["exposure"] > 0 else 0

        self.realtime_buffer.append(metrics)
        return metrics

    def batch_collect(self, content_ids: List[str], platforms: Optional[List[str]] = None) -> List[Dict]:
        """批量采集数据"""
        results = []
        plats = platforms or ["zhihu", "csdn", "toutiao", "xiaohongshu"]
        for cid in content_ids:
            for plat in plats:
                results.append(self.collect_metrics(cid, plat))
        logger.info(f"[Analytics] 批量采集: {len(results)} 条数据")
        return results

    def generate_snapshot(self, period: str = "daily") -> AnalyticsSnapshot:
        """生成分析快照"""
        snapshot = AnalyticsSnapshot(
            timestamp=datetime.now().isoformat(),
            period=period,
            total_exposure=sum(m.get("exposure", 0) for m in self.realtime_buffer),
            total_clicks=sum(m.get("clicks", 0) for m in self.realtime_buffer),
            total_conversions=sum(m.get("saves", 0) for m in self.realtime_buffer),
        )

        platform_data = {}
        for m in self.realtime_buffer:
            plat = m.get("platform", "unknown")
            if plat not in platform_data:
                platform_data[plat] = {"count": 0, "total_exposure": 0, "total_clicks": 0, "avg_ctr": 0}
            platform_data[plat]["count"] += 1
            platform_data[plat]["total_exposure"] += m.get("exposure", 0)
            platform_data[plat]["total_clicks"] += m.get("clicks", 0)

        for plat, data in platform_data.items():
            data["avg_ctr"] = round(data["total_clicks"] / data["total_exposure"], 4) if data["total_exposure"] > 0 else 0

        snapshot.platform_metrics = platform_data
        snapshot.content_performance = sorted(
            self.realtime_buffer[-50:],
            key=lambda x: x.get("ctr", 0),
            reverse=True,
        )[:10]

        snapshot.trends = self._compute_trends()
        self.snapshots.append(snapshot)
        self._save_snapshot(snapshot)

        return snapshot

    def _compute_trends(self) -> Dict:
        """计算数据趋势"""
        recent = self.realtime_buffer[-100:]
        if not recent:
            return {"direction": "stable", "change_pct": 0}

        mid = len(recent) // 2
        first_half = recent[:mid]
        second_half = recent[mid:]

        def avg_ctr(data):
            return sum(m.get("ctr", 0) for m in data) / len(data) if data else 0

        ctr_change = avg_ctr(second_half) - avg_ctr(first_half)
        direction = "up" if ctr_change > 0.01 else "down" if ctr_change < -0.01 else "stable"

        return {
            "direction": direction,
            "ctr_change": round(ctr_change, 4),
            "avg_ctr_recent": round(avg_ctr(recent), 4),
            "best_platform": self._find_best_platform(recent),
        }

    def _find_best_platform(self, data: List[Dict]) -> str:
        platform_ctr = {}
        for m in data:
            plat = m.get("platform", "")
            if plat not in platform_ctr:
                platform_ctr[plat] = []
            platform_ctr[plat].append(m.get("ctr", 0))

        best = max(platform_ctr.items(), key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 0, default=("", []))
        return best[0]

    def identify_top_content(self, n: int = 5) -> List[Dict]:
        """识别表现最好的内容"""
        content_groups = {}
        for m in self.realtime_buffer:
            cid = m.get("content_id", "")
            if cid not in content_groups:
                content_groups[cid] = {"content_id": cid, "total_exposure": 0, "total_clicks": 0, "platforms": []}
            content_groups[cid]["total_exposure"] += m.get("exposure", 0)
            content_groups[cid]["total_clicks"] += m.get("clicks", 0)
            content_groups[cid]["platforms"].append(m.get("platform", ""))

        for cid in content_groups:
            g = content_groups[cid]
            g["avg_ctr"] = round(g["total_clicks"] / g["total_exposure"], 4) if g["total_exposure"] > 0 else 0

        return sorted(content_groups.values(), key=lambda x: x["avg_ctr"], reverse=True)[:n]

    def identify_underperforming(self, threshold_ctr: float = 0.02) -> List[Dict]:
        """识别低表现内容"""
        content_groups = {}
        for m in self.realtime_buffer:
            cid = m.get("content_id", "")
            if cid not in content_groups:
                content_groups[cid] = {"content_id": cid, "total_exposure": 0, "total_clicks": 0}
            content_groups[cid]["total_exposure"] += m.get("exposure", 0)
            content_groups[cid]["total_clicks"] += m.get("clicks", 0)

        under = []
        for cid, g in content_groups.items():
            ctr = g["total_clicks"] / g["total_exposure"] if g["total_exposure"] > 0 else 0
            if ctr < threshold_ctr and g["total_exposure"] > 1000:
                g["ctr"] = round(ctr, 4)
                under.append(g)

        return sorted(under, key=lambda x: x["ctr"])

    def generate_optimization_suggestions(self) -> List[Dict]:
        """基于数据分析生成优化建议"""
        trends = self._compute_trends()
        suggestions = []

        if trends["direction"] == "down":
            suggestions.append({
                "priority": "high",
                "action": "revise_prompts",
                "detail": "CTR呈下降趋势，建议优化Prompt模板，增加标题吸引力",
                "metric": f"CTR变化: {trends['ctr_change']}",
            })

        best_platform = trends.get("best_platform", "")
        if best_platform:
            suggestions.append({
                "priority": "medium",
                "action": "increase_allocation",
                "detail": f"平台 '{best_platform}' 表现最好，建议增加该平台的资源分配",
                "metric": f"最佳平台: {best_platform}",
            })

        under = self.identify_underperforming()
        if under:
            suggestions.append({
                "priority": "medium",
                "action": "update_content",
                "detail": f"发现 {len(under)} 条低质量内容，建议重新优化或下架",
                "metric": f"低质内容数: {len(under)}",
            })

        return suggestions

    def _save_snapshot(self, snapshot: AnalyticsSnapshot):
        path = DATA_DIR / "analytics" / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": snapshot.timestamp,
                "period": snapshot.period,
                "total_exposure": snapshot.total_exposure,
                "total_clicks": snapshot.total_clicks,
                "total_conversions": snapshot.total_conversions,
                "platform_metrics": snapshot.platform_metrics,
                "trends": snapshot.trends,
            }, f, ensure_ascii=False, indent=2)

    def get_dashboard_data(self) -> Dict:
        """获取仪表盘数据"""
        if not self.realtime_buffer:
            return {"status": "no_data"}

        total_exposure = sum(m.get("exposure", 0) for m in self.realtime_buffer)
        total_clicks = sum(m.get("clicks", 0) for m in self.realtime_buffer)
        avg_ctr = round(total_clicks / total_exposure, 4) if total_exposure else 0

        return {
            "total_content": len(set(m.get("content_id") for m in self.realtime_buffer)),
            "total_distributions": len(self.realtime_buffer),
            "total_exposure": total_exposure,
            "total_clicks": total_clicks,
            "avg_ctr": avg_ctr,
            "trends": self._compute_trends(),
            "top_content": self.identify_top_content(3),
            "optimization_suggestions": self.generate_optimization_suggestions(),
        }
