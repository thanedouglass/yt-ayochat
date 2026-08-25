"""Base classes and schemas for RAG evaluation metrics."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MetricResult:
    """Standardized outcome of evaluating a metric."""
    name: str
    score: float
    threshold: float
    passed: bool
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 4),
            "threshold": round(self.threshold, 4),
            "passed": self.passed,
            "reason": self.reason,
            "details": self.details,
        }


class BaseMetric(ABC):
    """Abstract interface for RAG quality and security metrics."""

    def __init__(self, name: str, threshold: float = 0.8) -> None:
        self.name = name
        self.threshold = threshold

    @abstractmethod
    def evaluate(self, **kwargs: Any) -> MetricResult:
        """Compute the metric score and return a MetricResult."""
        pass
