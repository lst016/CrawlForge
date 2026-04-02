"""
Template Store - manages screenshot templates for visual matching.

Provides storage, retrieval, and versioning of template images used for
fallback visual detection when AI-based detection fails.
"""

import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Template:
    """A screenshot template for visual matching."""
    name: str
    category: str  # e.g., "button", "screen", "ui_element"
    game_name: str
    file_path: str  # Relative path within store
    md5_hash: str
    width: int
    height: int
    threshold: float = 0.8  # Match confidence threshold
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    version: int = 1
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "game_name": self.game_name,
            "file_path": self.file_path,
            "md5_hash": self.md5_hash,
            "width": self.width,
            "height": self.height,
            "threshold": self.threshold,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Template":
        return cls(**d)


@dataclass
class MatchResult:
    """Result of template matching."""
    template: Template
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    center: tuple[int, int]
    matched: bool


class TemplateStore:
    """
    Manages template images and metadata for visual matching.

    Storage structure:
        store_root/
            templates/
                <game_name>/
                    <category>/
                        <template_name>.png
            metadata/
                templates.json       # All template metadata
                categories.json      # Category index
                games.json           # Game index
    """

    def __init__(self, store_root: Path):
        """
        Args:
            store_root: Root directory of the template store.
        """
        self.store_root = Path(store_root)
        self.templates_dir = self.store_root / "templates"
        self.metadata_dir = self.store_root / "metadata"
        self._index: dict[str, Template] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load template index from metadata file."""
        index_file = self.metadata_dir / "templates.json"
        if index_file.exists():
            with open(index_file) as f:
                data = json.load(f)
                for d in data.values():
                    t = Template.from_dict(d)
                    self._index[t.name] = t

    def _save_index(self) -> None:
        """Save template index to metadata file."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        index_file = self.metadata_dir / "templates.json"
        data = {name: t.to_dict() for name, t in self._index.items()}
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)

    def _ensure_dirs(self, game_name: str, category: str) -> Path:
        """Ensure template directory exists."""
        dir_path = self.templates_dir / game_name / category
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def add(
        self,
        image_data: bytes,
        name: str,
        game_name: str,
        category: str,
        description: str = "",
        tags: list[str] = None,
        threshold: float = 0.8,
        metadata: dict = None,
    ) -> Template:
        """
        Add a template to the store.

        Args:
            image_data: PNG image bytes.
            name: Template name.
            game_name: Game this template belongs to.
            category: Template category (button, screen, etc.).
            description: Human-readable description.
            tags: Searchable tags.
            threshold: Match confidence threshold.
            metadata: Additional metadata.

        Returns:
            The created Template.
        """
        import struct
        import zlib

        # Calculate MD5
        md5_hash = hashlib.md5(image_data).hexdigest()

        # Get image dimensions (PNG)
        width, height = self._get_png_dimensions(image_data)

        # Save image file
        dir_path = self._ensure_dirs(game_name, category)
        file_path = dir_path / f"{name}.png"
        file_path.write_bytes(image_data)

        # Create template
        template = Template(
            name=name,
            category=category,
            game_name=game_name,
            file_path=str(file_path.relative_to(self.store_root)),
            md5_hash=md5_hash,
            width=width,
            height=height,
            threshold=threshold,
            description=description,
            tags=tags or [],
            created_at=datetime.now().isoformat(),
            version=1,
            metadata=metadata or {},
        )

        self._index[name] = template
        self._save_index()
        return template

    def get(self, name: str) -> Optional[Template]:
        """Get template by name."""
        return self._index.get(name)

    def get_by_game(self, game_name: str) -> list[Template]:
        """Get all templates for a game."""
        return [t for t in self._index.values() if t.game_name == game_name]

    def get_by_category(self, category: str) -> list[Template]:
        """Get all templates in a category."""
        return [t for t in self._index.values() if t.category == category]

    def get_by_game_category(self, game_name: str, category: str) -> list[Template]:
        """Get templates filtered by game and category."""
        return [
            t for t in self._index.values()
            if t.game_name == game_name and t.category == category
        ]

    def search(self, query: str) -> list[Template]:
        """Search templates by name, description, or tags."""
        q = query.lower()
        results = []
        for t in self._index.values():
            if q in t.name.lower() or q in t.description.lower():
                results.append(t)
                continue
            if any(q in tag.lower() for tag in t.tags):
                results.append(t)
        return results

    def remove(self, name: str) -> bool:
        """Remove a template from the store."""
        template = self._index.pop(name, None)
        if template is None:
            return False

        file_path = self.store_root / template.file_path
        if file_path.exists():
            file_path.unlink()

        self._save_index()
        return True

    def update(self, name: str, **kwargs) -> Optional[Template]:
        """Update template metadata."""
        template = self._index.get(name)
        if template is None:
            return None

        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)

        template.version += 1
        self._save_index()
        return template

    def list_all(self) -> list[Template]:
        """List all templates."""
        return list(self._index.values())

    def list_games(self) -> list[str]:
        """List all known game names."""
        return sorted(set(t.game_name for t in self._index.values()))

    def list_categories(self) -> list[str]:
        """List all known categories."""
        return sorted(set(t.category for t in self._index.values()))

    @staticmethod
    def _get_png_dimensions(data: bytes) -> tuple[int, int]:
        """Extract width/height from PNG data without Pillow."""
        # PNG signature + IHDR chunk
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return width, height

    def get_image_path(self, template: Template) -> Path:
        """Get absolute path to template image."""
        return self.store_root / template.file_path
