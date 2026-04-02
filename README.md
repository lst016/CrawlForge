# CrawlForge

> AI-driven multi-game crawler framework.

每个游戏都有自己专属的 AI 生成适配器，完全由 AI 驱动、自动进化。

## 核心理念

- **AI First**: 所有爬虫代码由 AI 自动生成
- **Self-Evolving**: 游戏更新后 AI 自动检测并修复适配器
- **Game Adapter**: 每个游戏 = 一个 Adapter，标准化接口
- **Multi-Runtime**: 支持页游(Playwright)、手游(ADB)、PC游戏(Win32)

## 系统架构

```
CrawlForge
├── core/                    # 核心框架
│   ├── orchestrator.py      # AI 任务编排器
│   ├── adapter.py          # 游戏适配器基类
│   ├── registry.py         # 适配器注册中心
│   └── evolution.py        # 自我进化引擎
├── runtimes/               # 多运行时
│   ├── playwright/          # 页游/H5 运行时
│   ├── adb/                # 手游 ADB 运行时
│   └── win32/              # PC 游戏运行时
├── adapters/               # 各游戏适配器（AI 生成）
│   ├── genshin/            # 原神
│   ├── honkai_starrail/    # 崩铁
│   └── ...
├── ai/                     # AI 集成
│   ├── generator.py         # 适配器代码生成
│   └── detector.py         # 失效检测
└── tests/                  # 测试
```

## 快速开始

```python
from crawlforge import CrawlForge

# 创建爬虫实例
cf = CrawlForge()

# AI 自动分析并生成适配器
adapter = await cf.generate_adapter("原神")

# 爬取数据
data = await adapter.extract(gold_info)
print(data)
```

## 适配器示例

```python
from crawlforge.adapters import GameAdapter

class GenshinAdapter(GameAdapter):
    async def detect_state(self, screenshot):
        # AI 识别当前游戏界面状态
        ...

    async def generate_action(self, state, goal):
        # AI 生成下一步操作
        ...

    async def extract_data(self, state):
        # 提取游戏数据
        ...
```

## License

MIT
