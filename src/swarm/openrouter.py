"""Re-export of backend/openrouter.py for src.swarm package."""

from backend.openrouter import (
    CouncilModelConfig,
    OpenRouterClient,
    REGIONAL_COUNCIL_REGISTRY,
    openrouter_client,
)

__all__ = [
    "CouncilModelConfig",
    "OpenRouterClient",
    "REGIONAL_COUNCIL_REGISTRY",
    "openrouter_client",
]
