"""
TemplateStore - Storage for slot game UI templates.

Manages template images used for template matching in game automation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Dict

from ..core.exceptions import RuntimeError


class TemplateStore:
    """
    CRUD operations for slot game templates.

    Templates are stored in a directory with JSON metadata.
    """

    def __init__(self, templates_dir: str = "./templates"):
        """
        Args:
            templates_dir: Directory to store templates.
        """
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._meta_file = self.templates_dir / "meta.json"
        self._meta: Dict = self._load_meta()

    def _load_meta(self) -> Dict:
        """Load metadata from disk."""
        if self._meta_file.exists():
            try:
                return json.loads(self._meta_file.read_text())
            except Exception:
                return {}
        return {}

    def _save_meta(self) -> None:
        """Save metadata to disk."""
        self._meta_file.write_text(json.dumps(self._meta, indent=2))

    def add(
        self,
        name: str,
        template_path: str,
        template_type: str,
        description: str = "",
    ) -> Dict:
        """
        Add a new template.

        Args:
            name: Unique template name.
            template_path: Path to template image file.
            template_type: Type like "spin_button", "balance", "bonus_icon".
            description: Optional description.

        Returns:
            Template metadata dict.
        """
        if name in self._meta:
            raise RuntimeError(f"Template '{name}' already exists")

        meta = {
            "name": name,
            "path": template_path,
            "type": template_type,
            "description": description,
        }
        self._meta[name] = meta
        self._save_meta()
        return meta

    def get(self, name: str) -> Optional[Dict]:
        """Get template metadata by name."""
        return self._meta.get(name)

    def list(self, template_type: Optional[str] = None) -> List[Dict]:
        """
        List all templates, optionally filtered by type.

        Args:
            template_type: Filter by type (e.g., "spin_button").

        Returns:
            List of template metadata dicts.
        """
        templates = list(self._meta.values())
        if template_type:
            templates = [t for t in templates if t.get("type") == template_type]
        return templates

    def update(self, name: str, **kwargs) -> Dict:
        """
        Update template metadata.

        Args:
            name: Template name to update.
            **kwargs: Fields to update.

        Returns:
            Updated template metadata.
        """
        if name not in self._meta:
            raise RuntimeError(f"Template '{name}' not found")
        self._meta[name].update(kwargs)
        self._save_meta()
        return self._meta[name]

    def delete(self, name: str) -> bool:
        """
        Delete a template.

        Args:
            name: Template name to delete.

        Returns:
            True if deleted.
        """
        if name not in self._meta:
            return False
        del self._meta[name]
        self._save_meta()
        return True

    def get_by_type(self, template_type: str) -> List[Dict]:
        """Get all templates of a specific type."""
        return self.list(template_type)
