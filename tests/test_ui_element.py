"""
Tests for UIElement.
"""

import pytest
from crawlforge.uiauto.ui_element import UIElement


def test_ui_element_defaults():
    el = UIElement()
    assert el.resource_id == ""
    assert el.text == ""
    assert el.bounds == (0, 0, 0, 0)
    assert el.children == []


def test_ui_element_center():
    el = UIElement(bounds=(100, 200, 300, 400))
    cx, cy = el.center
    assert cx == 200
    assert cy == 300


def test_ui_element_bounds_dict():
    el = UIElement(bounds=(10, 20, 110, 120))
    d = el.bounds_dict
    assert d == {"x1": 10, "y1": 20, "x2": 110, "y2": 120}


def test_find_child():
    parent = UIElement(children=[
        UIElement(resource_id="btn_spin"),
        UIElement(resource_id="btn_back"),
    ])
    found = parent.find_child(resource_id="btn_spin")
    assert found is not None
    assert found.resource_id == "btn_spin"


def test_find_child_nested():
    parent = UIElement(children=[
        UIElement(children=[
            UIElement(resource_id="nested"),
        ]),
    ])
    found = parent.find_child(resource_id="nested")
    assert found is not None


def test_find_child_no_match():
    parent = UIElement(children=[UIElement(resource_id="btn")])
    assert parent.find_child(resource_id="missing") is None


def test_find_all():
    parent = UIElement(children=[
        UIElement(class_name="Button"),
        UIElement(class_name="TextView"),
        UIElement(class_name="Button"),
    ])
    buttons = parent.find_all(class_name="Button")
    assert len(buttons) == 2


def test_to_dict():
    el = UIElement(
        resource_id="test",
        text="Hello",
        bounds=(0, 0, 100, 50),
        children=[UIElement(resource_id="child")],
    )
    d = el.to_dict()
    assert d["resource_id"] == "test"
    assert d["text"] == "Hello"
    assert len(d["children"]) == 1


def test_matches():
    el = UIElement(resource_id="btn", text="Spin", clickable=True, enabled=True)
    assert UIElement._matches(el, {"resource_id": "btn", "clickable": True})
    assert not UIElement._matches(el, {"resource_id": "wrong"})
