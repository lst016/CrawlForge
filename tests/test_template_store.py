"""
Tests for TemplateStore.
"""

import pytest
import tempfile
from pathlib import Path
from crawlforge.template_store import TemplateStore, Template


# Minimal 1x1 PNG
MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
    b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_template_store_init():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TemplateStore(Path(tmpdir))
        assert store.list_all() == []


def test_template_store_add():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TemplateStore(Path(tmpdir))
        t = store.add(MINIMAL_PNG, "spin_btn", "GameA", "button", description="Spin button")
        assert t.name == "spin_btn"
        assert t.game_name == "GameA"
        assert t.category == "button"
        assert t.width == 1
        assert t.height == 1


def test_template_store_get():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TemplateStore(Path(tmpdir))
        store.add(MINIMAL_PNG, "spin", "GameA", "button")
        t = store.get("spin")
        assert t is not None
        assert t.name == "spin"


def test_template_store_get_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TemplateStore(Path(tmpdir))
        assert store.get("nonexistent") is None


def test_template_store_get_by_game():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TemplateStore(Path(tmpdir))
        store.add(MINIMAL_PNG, "t1", "GameA", "button")
        store.add(MINIMAL_PNG, "t2", "GameA", "button")
        store.add(MINIMAL_PNG, "t3", "GameB", "button")
        results = store.get_by_game("GameA")
        assert len(results) == 2


def test_template_store_get_by_category():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TemplateStore(Path(tmpdir))
        store.add(MINIMAL_PNG, "t1", "GameA", "button")
        store.add(MINIMAL_PNG, "t2", "GameA", "screen")
        results = store.get_by_category("button")
        assert len(results) == 1


def test_template_store_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TemplateStore(Path(tmpdir))
        store.add(MINIMAL_PNG, "main_spin", "GameA", "button", description="Main spin")
        store.add(MINIMAL_PNG, "auto_spin", "GameA", "button", tags=["auto", "spin"])
        results = store.search("spin")
        assert len(results) == 2


def test_template_store_remove():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TemplateStore(Path(tmpdir))
        store.add(MINIMAL_PNG, "t1", "GameA", "button")
        assert store.remove("t1") is True
        assert store.get("t1") is None


def test_template_store_update():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TemplateStore(Path(tmpdir))
        store.add(MINIMAL_PNG, "t1", "GameA", "button")
        updated = store.update("t1", description="Updated", threshold=0.9)
        assert updated.description == "Updated"
        assert updated.threshold == 0.9
        assert updated.version == 2


def test_template_to_dict():
    t = Template(
        name="test", category="btn", game_name="Game",
        file_path="t.png", md5_hash="abc", width=100, height=50,
        version=1,
    )
    d = t.to_dict()
    assert d["name"] == "test"
    assert d["width"] == 100
