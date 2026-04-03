"""
Game Adapter module - pluggable adapters for different game types.

Provides:
- GameAdapter: Abstract base class for all adapters
- AdapterConfig: Configuration dataclass
- AdapterMetadata: Metadata about adapters
- AdapterRegistry: Central registry for adapter classes
- Concrete adapters: SlotGameAdapter, PokerGameAdapter, ArcadeGameAdapter
"""

from .base import (
    GameAdapter,
    AdapterConfig,
    AdapterMetadata,
    GameAdapterMixin,
)
from .slot_adapter import SlotGameAdapter
from .poker_adapter import PokerGameAdapter
from .arcade_adapter import ArcadeGameAdapter
from .registry import (
    AdapterRegistry,
    RegisteredAdapter,
    get_registry,
    register_adapter,
    create_adapter,
)

__all__ = [
    # Base
    "GameAdapter",
    "AdapterConfig",
    "AdapterMetadata",
    "GameAdapterMixin",
    # Concrete adapters
    "SlotGameAdapter",
    "PokerGameAdapter",
    "ArcadeGameAdapter",
    # Registry
    "AdapterRegistry",
    "RegisteredAdapter",
    "get_registry",
    "register_adapter",
    "create_adapter",
]
