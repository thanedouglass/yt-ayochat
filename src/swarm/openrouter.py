"""Re-export of src/backend/openrouter.py for src.swarm package."""

try:
    from src.backend.openrouter import (
        CouncilModelConfig,
        OpenRouterClient,
        REGIONAL_COUNCIL_REGISTRY,
        openrouter_client,
    )
except ImportError:
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

