# CrawlForge - AI-Driven Slot Game Crawler Framework

## 项目概述

CrawlForge 是一个自进化的多运行时爬虫框架，用于自动玩 + 采集游戏数据（老虎机、棋牌类）。

## 技术栈

- **运行时**: ADB + uiautomator2 (Android), Playwright (Web)
- **AI**: newapi (本地 LLM 代理，端口 5337)
- **视觉**: OpenCV 模板匹配 + AI vision fallback
- **自愈**: Checkpoint + AdapterFixer (evolution)
- **语言**: Python 3.9+

## 关键模块

| 模块 | 路径 | 状态 |
|------|------|------|
| AI Pipeline | `crawlforge/ai_pipeline/` | ✅ |
| ReAct Loop | `crawlforge/react/loop.py` | ✅ |
| Runtime 抽象 | `crawlforge/runtimes/` | ✅ |
| Adapter | `crawlforge/adapter/` | ✅ |
| Checkpoint | `crawlforge/checkpoint/` | ✅ |
| Data Collector | `crawlforge/data/` | ✅ |
| Evolution | `crawlforge/evolution/` | ✅ |
| Template Matching | `crawlforge/template_matching/` | ✅ |
| Slot Detector | `crawlforge/detector/` | ✅ |
| Scheduler | `crawlforge/scheduler/` | ✅ |
| Template Store | `crawlforge/template_store/` | ✅ |
| UI Auto | `crawlforge/uiauto/` | ✅ |

## 环境变量

```bash
# AI Backend (newapi)
NEWAPI_URL=http://localhost:5337/v1
NEWAPI_KEY=your_key_here
VISION_MODEL=MiniMax-M2.7
CHAT_MODEL=MiniMax-M2.5-highspeed

# 其他后端
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
OLLAMA_URL=http://localhost:11434
```

## 开发约定

- 所有异步方法使用 `async def`
- 新模块需添加 `__all__` 导出
- 配置类使用 `@dataclass`
- 错误处理: 具体异常类，非 bare `except`
- OpenCV 相关只在 `template_matching/` 中使用

## Win 迁移注意

- ADB Runtime 依赖 Android SDK (Windows 兼容)
- Playwright Runtime 多平台支持，无需改动
- `template_matching/` 纯 Python + OpenCV，跨平台

## 运行测试

```bash
pytest tests/ -v
```
