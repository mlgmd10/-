import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class PlatformConfig:
    name: str
    api_endpoint: str = ""
    content_max_length: int = 5000
    supported_formats: List[str] = field(default_factory=lambda: ["text"])
    posting_schedule: str = "every 2 hours"
    enabled: bool = True


@dataclass
class AgentConfig:
    max_rounds: int = 5
    temperature: float = 0.7
    model: str = "gpt-4"
    reply_timeout: int = 120
    max_retries: int = 3


@dataclass
class GEOConfig:
    topics_source: str = "trending"
    content_templates_path: str = "data/templates"
    ab_test_ratio: float = 0.3
    min_quality_score: float = 0.7
    iteration_limit: int = 10
    prompt_optimization_enabled: bool = True


@dataclass
class SchedulerConfig:
    interval_minutes: int = 30
    max_concurrent_tasks: int = 5
    retry_on_failure: bool = True
    max_retries: int = 3
    quiet_hours_start: int = 2
    quiet_hours_end: int = 6


@dataclass
class Config:
    platforms: List[PlatformConfig] = field(default_factory=lambda: [
        PlatformConfig(name="wechat_mp", api_endpoint="", content_max_length=20000, supported_formats=["text", "image", "rich_text"]),
        PlatformConfig(name="zhihu", api_endpoint="", content_max_length=10000, supported_formats=["text", "image", "rich_text"]),
        PlatformConfig(name="xiaohongshu", api_endpoint="", content_max_length=1000, supported_formats=["text", "image"]),
        PlatformConfig(name="toutiao", api_endpoint="", content_max_length=5000, supported_formats=["text", "image", "video"]),
        PlatformConfig(name="csdn", api_endpoint="", content_max_length=20000, supported_formats=["text", "code", "image"]),
    ])
    agent: AgentConfig = field(default_factory=AgentConfig)
    geo: GEOConfig = field(default_factory=GEOConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    output_dir: str = str(BASE_DIR / "output")
    data_dir: str = str(BASE_DIR / "data")
    logs_dir: str = str(BASE_DIR / "logs")

    def save(self, path: str = "config.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, ensure_ascii=False, indent=2, default=lambda o: o.__dict__)

    @classmethod
    def load(cls, path: str = "config.json") -> "Config":
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = cls()
        if "platforms" in data:
            config.platforms = [PlatformConfig(**p) for p in data["platforms"]]
        if "agent" in data:
            config.agent = AgentConfig(**data["agent"])
        if "geo" in data:
            config.geo = GEOConfig(**data["geo"])
        if "scheduler" in data:
            config.scheduler = SchedulerConfig(**data["scheduler"])
        return config


config = Config()
