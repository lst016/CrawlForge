"""
Tests for UIElementEncoder.
"""

import pytest
from crawlforge.uiauto.runtime import UIElementEncoder


SIMPLE_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="com.game:id/root" class="android.widget.FrameLayout" package="com.game" content-desc="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" scrollable="false" bounds="[0,0][1080,2340]">
    <node text="Balance: 5000" resource-id="com.game:id/balance" class="android.widget.TextView" clickable="false" enabled="true" bounds="[100,100][300,150]"/>
    <node text="SPIN" resource-id="com.game:id/spin_btn" class="android.widget.Button" clickable="true" enabled="true" bounds="[400,2000][680,2100]"/>
  </node>
</hierarchy>"""


def test_parse_hierarchy_basic():
    root = UIElementEncoder.parse_hierarchy(SIMPLE_XML)
    assert root.resource_id == "com.game:id/root"
    assert root.class_name == "android.widget.FrameLayout"
    assert root.bounds == (0, 0, 1080, 2340)
    assert root.enabled is True


def test_parse_hierarchy_children():
    root = UIElementEncoder.parse_hierarchy(SIMPLE_XML)
    assert len(root.children) == 2

    balance = root.children[0]
    assert balance.text == "Balance: 5000"
    assert balance.resource_id == "com.game:id/balance"
    assert balance.bounds == (100, 100, 300, 150)
    assert balance.clickable is False

    spin = root.children[1]
    assert spin.text == "SPIN"
    assert spin.resource_id == "com.game:id/spin_btn"
    assert spin.bounds == (400, 2000, 680, 2100)
    assert spin.clickable is True


def test_parse_hierarchy_depth():
    root = UIElementEncoder.parse_hierarchy(SIMPLE_XML)
    assert root.depth == 0
    assert root.children[0].depth == 1
    assert root.children[1].depth == 1


def test_parse_bounds():
    assert UIElementEncoder._parse_bounds("[0,0][1080,2340]") == (0, 0, 1080, 2340)
    assert UIElementEncoder._parse_bounds("[100,200][500,600]") == (100, 200, 500, 600)
    assert UIElementEncoder._parse_bounds("invalid") == (0, 0, 0, 0)


def test_str_to_basic():
    assert UIElementEncoder._str_to_basic("true") is True
    assert UIElementEncoder._str_to_basic("false") is False
    assert UIElementEncoder._str_to_basic("123") == 123
    assert UIElementEncoder._str_to_basic("-456") == -456
    assert UIElementEncoder._str_to_basic("3.14") == 3.14
    assert UIElementEncoder._str_to_basic("hello") == "hello"
