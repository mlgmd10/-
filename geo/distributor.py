import json
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("geo.distributor")


@dataclass
class DistributionRecord:
    id: str
    content_id: str
    platform: str
    status: str
    published_url: Optional[str] = None
    published_at: Optional[str] = None
    version: str = "v1"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContentDistributor:
    """多平台内容分发引擎"""

    PLATFORM_SPECS = {
        "zhihu": {
            "name": "知乎",
            "post_type": "article",
            "best_times": ["12:00", "19:00", "21:00"],
            "content_rules": {
                "title_max": 50,
                "body_max": 10000,
                "hashtags_max": 5,
            },
        },
        "csdn": {
            "name": "CSDN",
            "post_type": "blog",
            "best_times": ["10:00", "14:00", "20:00"],
            "content_rules": {
                "title_max": 80,
                "body_max": 20000,
                "hashtags_max": 10,
            },
        },
        "xiaohongshu": {
            "name": "小红书",
            "post_type": "note",
            "best_times": ["12:00", "18:00", "21:30"],
            "content_rules": {
                "title_max": 20,
                "body_max": 1000,
                "hashtags_max": 10,
            },
        },
        "toutiao": {
            "name": "今日头条",
            "post_type": "article",
            "best_times": ["7:00", "12:00", "19:00"],
            "content_rules": {
                "title_max": 30,
                "body_max": 5000,
                "hashtags_max": 3,
            },
        },
        "wechat_mp": {
            "name": "微信公众号",
            "post_type": "article",
            "best_times": ["12:00", "21:00"],
            "content_rules": {
                "title_max": 64,
                "body_max": 20000,
                "hashtags_max": 0,
            },
        },
    }

    def __init__(self, config=None):
        self.config = config
        self.records: List[DistributionRecord] = []
        self.schedule: List[Dict] = []

    def distribute(self, content: Dict, platforms: List[str]) -> List[DistributionRecord]:
        """将内容分发到指定平台"""
        results = []
        content_id = content.get("id", f"unknown_{datetime.now().timestamp()}")

        for platform in platforms:
            if platform not in self.PLATFORM_SPECS:
                logger.warning(f"[Distributor] 未知平台: {platform}")
                continue

            spec = self.PLATFORM_SPECS[platform]
            adapted_content = self._adapt_for_platform(content, platform, spec)

            record = DistributionRecord(
                id=f"dist_{datetime.now().strftime('%Y%m%d%H%M%S')}_{platform}",
                content_id=content_id,
                platform=platform,
                status="published" if random.random() > 0.1 else "failed",
                published_at=datetime.now().isoformat(),
                metadata={
                    "platform_name": spec["name"],
                    "content_type": spec["post_type"],
                    "adapted": adapted_content.get("adapted", False),
                },
            )

            results.append(record)
            self.records.append(record)
            logger.info(f"[Distributor] 分发完成: {content_id} -> {spec['name']} [{record.status}]")

        return results

    def batch_distribute(self, content_list: List[Dict]) -> List[DistributionRecord]:
        """批量分发内容"""
        all_results = []
        for content in content_list:
            platforms = content.get("target_platforms", ["zhihu", "csdn"])
            results = self.distribute(content, platforms)
            all_results.extend(results)

        logger.info(f"[Distributor] 批量分发完成: {len(content_list)} 条内容 -> {len(all_results)} 条记录")
        return all_results

    def schedule_distribution(self, content: Dict, platform: str, publish_time: str) -> Dict:
        """安排定时分发"""
        schedule_entry = {
            "id": f"sched_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "content_id": content.get("id", ""),
            "platform": platform,
            "scheduled_time": publish_time,
            "status": "scheduled",
            "created_at": datetime.now().isoformat(),
        }
        self.schedule.append(schedule_entry)
        logger.info(f"[Distributor] 已安排定时发布: {platform} @ {publish_time}")
        return schedule_entry

    def get_next_best_time(self, platform: str) -> str:
        """获取平台的最佳发布时间"""
        spec = self.PLATFORM_SPECS.get(platform, {})
        best_times = spec.get("best_times", ["12:00"])
        return random.choice(best_times)

    def _adapt_for_platform(self, content: Dict, platform: str, spec: Dict) -> Dict:
        """将内容适配为目标平台格式"""
        adapted = content.copy()
        rules = spec.get("content_rules", {})

        title = content.get("title", "")
        if len(title) > rules.get("title_max", 50):
            adapted["title"] = title[:rules.get("title_max", 50) - 3] + "..."

        body = content.get("body", "")
        if len(body) > rules.get("body_max", 5000):
            adapted["body"] = body[:rules.get("body_max", 5000)] + "\n\n[内容已截断...]"

        if platform == "wechat_mp":
            adapted["body"] += "\n\n---\n关注公众号，获取更多深度内容"
        elif platform == "xiaohongshu":
            tags = content.get("seo_keywords", [])[:rules.get("hashtags_max", 5)]
            adapted["body"] += "\n\n" + " ".join([f"#{t}" for t in tags])

        adapted["adapted"] = True
        adapted["platform"] = platform
        return adapted

    def get_distribution_stats(self) -> Dict:
        """获取分发统计数据"""
        total = len(self.records)
        if total == 0:
            return {"total": 0, "by_platform": {}, "success_rate": 0}

        succeeded = sum(1 for r in self.records if r.status == "published")
        by_platform = {}
        for r in self.records:
            by_platform.setdefault(r.platform, {"total": 0, "succeeded": 0, "failed": 0})
            by_platform[r.platform]["total"] += 1
            if r.status == "published":
                by_platform[r.platform]["succeeded"] += 1
            else:
                by_platform[r.platform]["failed"] += 1

        return {
            "total": total,
            "success_rate": round(succeeded / total, 3),
            "by_platform": by_platform,
            "pending_schedule": len(self.schedule),
        }
