# Game Automation + AI Agent Harness Landscape

Research Date: 2026-04-02

---

## Game Automation Projects

### mpcabete/bombcrypto-bot (⭐811)
**URL:** https://github.com/mpcabete/bombcrypto-bot

### Description
A Python bot for the BombCrypto game that automatically logs in, clicks "new map" buttons, and sends heroes to work. Uses image recognition (template matching) to detect game UI elements.

### Key Technical Insights
- **Image-based detection**: Uses `opencv` and `numpy` for template matching against screenshots
- **Configurable thresholds**: `config.yaml` controls sensitivity for button detection
- **Screen-relative positioning**: Takes screenshots, matches images, clicks based on coordinates
- **State machine logic**: Checks disconnection → re-login flow, "new map" detection, hero work cycles
- **No game API interaction**: Bot only simulates mouse movements based on visual detection
- **Target images stored in `/targets/`**: Hero screenshots for "send home" feature

### What CrawlForge Can Learn From It
- Image/template matching as fallback when DOM/CSS selectors unavailable
- Threshold configuration for sensitivity tuning across different environments
- Modular target images approach for game-specific elements
- Non-intrusive detection that mimics human observation

### Integration Possibility
**High** — The screen-capture + image-matching pattern is directly applicable to browser-based games. Could be adapted as a fallback adapter when Playwright's standard selectors fail (e.g., canvas-based games, WebGL content).

---

### masterking32/MasterHamsterKombatBot (⭐257)
**URL:** https://github.com/masterking32/MasterHamsterKombatBot

### Description
Bot for Hamster Kombat (Telegram clicker game), one of the most popular Telegram mini-games.

### Key Technical Insights
- Telegram bot integration (Telegram Game API)
- Auto-clicker with configurable intervals
- HTTP-based API interaction with Telegram
- Proxy support for scaling

### What CrawlForge Can Learn From It
- Telegram mini-game integration patterns
- Simple HTTP-based game automation
- Mobile-first game automation approach

### Integration Possibility
**Medium** — Telegram integration would add support for popular Telegram games. Could be a separate runtime adapter.

---

### paulonteri/play-game-with-computer-vision (⭐134)
**URL:** https://github.com/paulonteri/play-game-with-computer-vision

### Description
Play games using computer vision and deep learning - detects game elements via screen capture and neural networks.

### Key Technical Insights
- Computer vision for game state detection
- Screen capture + CNN-based recognition
- Action selection via ML models

### What CrawlForge Can Learn From It
- ML-based game state understanding
- End-to-end learning for game automation

### Integration Possibility
**Medium** — Computer vision approach could enhance CrawlForge's ability to handle complex visual games beyond template matching.

---

### steve1316/granblue-automation-pyautogui (⭐133)
**URL:** https://github.com/steve1316/granblue-automation-pyautogui

### Description
Full browser-based game automation using `pyautogui` for Granblue Fantasy - a Japanese gacha game with complex UI.

### Key Technical Insights
- Browser-based automation with full-page screenshots
- Pyautogui for mouse/keyboard simulation
- Image recognition for button detection
- Robust reconnection and error handling
- Configurable settings for different display resolutions

### What CrawlForge Can Learn From It
- Cross-resolution compatibility patterns
- Comprehensive error handling and recovery
- Time-based action cooldowns

### Integration Possibility
**High** — Similar to bombcrypto-bot but more mature. Could contribute to a "visual fallback" adapter module.

---

### darkmatter2222/EVE-Online-Bot (⭐127)
**URL:** https://github.com/darkmatter2222/EVE-Online-Bot

### Description
Bot for EVE Online (complex MMORPG) using direct memory reading and game client hooking.

### Key Technical Insights
- Memory reading / memory hacking approach
- Direct game client manipulation (not visual-based)
- Complex state tracking for in-game systems

### What CrawlForge Can Learn From It
- Advanced techniques for desktop game automation
- Memory-level game state access

### Integration Possibility
**Low** — Too specific to EVE Online's architecture; would require entirely different approach (native memory access vs browser-based).

---

### Ikabot-Collective/ikabot (⭐121)
**URL:** https://github.com/Ikabot-Collective/ikabot

### Description
Multi-game bot framework supporting various online games (Instagram bots, multiple game types).

### Key Technical Insights
- Plugin-based architecture for different games
- Web automation approach
- Session management and authentication handling

### What CrawlForge Can Learn From It
- Plugin/extension pattern for game-specific modules
- Unified interface for diverse game types

### Integration Possibility
**Medium** — Architecture patterns could inspire CrawlForge's plugin system.

---

## AI Agent Harness Frameworks

### aden-hive/hive (⭐9,993)
**URL:** https://github.com/aden-hive/hive

### Description
Production-ready agent harness for AI agents - "the agent harness for production workloads." Provides state management, failure recovery, observability, and human oversight.

### Key Technical Insights
- **Runtime harness architecture**: Manages agent lifecycle, state persistence, crash recovery
- **Checkpoint-based recovery**: Agents can resume from failures without losing progress
- **Self-healing**: Captures failure data, evolves agent graphs automatically
- **Human-in-the-loop nodes**: Built-in oversight and intervention points
- **Cost enforcement**: Tracks and limits compute costs
- **Browser control integration**: Can control browsers for web tasks
- **Multi-agent coordination**: Session isolation and shared memory for teams
- **Queen/worker pattern**: Coding agent generates agent graphs

### What CrawlForge Can Learn From It
- Checkpoint/recovery system for long-running crawl jobs
- Production observability (logging, cost tracking, error reporting)
- Self-healing patterns when pages change or fail
- Human-in-the-loop for approval at critical steps

### Integration Possibility
**Very High** — Hive's production harness patterns are directly applicable to CrawlForge's enterprise/serious-use cases.

---

### aristoteleo/PantheonOS (⭐353)
**URL:** https://github.com/aristoteleo/PantheonOS

### Description
"Evolvable, distributed agent framework & harness for data science." Multi-agent system with genetic-algorithm-driven code evolution.

### Key Technical Insights
- **Agentic code evolution**: Agents can modify and improve their own algorithms
- **Multi-agent teams**: Sequential, Swarm, Mixture-of-Agents patterns
- **NATS-based distributed messaging**: Scalable fault-tolerant architecture
- **1,000+ curated agents** available via Pantheon Store
- **Evolve module**: Genetic algorithm-driven optimization of agent code
- **Privacy-preserving**: Designed for sensitive data (single-cell biology focus)

### What CrawlForge Can Learn From It
- Agent self-improvement through evolution
- Distributed/hierarchical agent architectures
- Marketplace pattern for sharing crawl strategies
- NATS for agent-to-agent communication

### Integration Possibility
**High** — The evolvable agent concept could help CrawlForge adapt to changing websites autonomously.

---

### vortezwohl/Autono (⭐209)
**URL:** https://github.com/vortezwohl/Autono

### Description
"A ReAct-Based Highly Robust Autonomous Agent Framework." Focuses on adaptive decision-making and multi-agent collaboration with robust failure handling.

### Key Technical Insights
- **ReAct paradigm**: Reasoning + Acting loop
- **Timely abandonment strategy**: Probabilistic penalty mechanism for task termination
- **Memory transfer mechanism**: Shared dynamic memory among agents
- **MCP protocol support**: Model Context Protocol for tool integration
- **Multi-agent collaboration**: Explicit division of labor
- **Adaptive execution**: Dynamically generates next actions based on prior trajectories
- **Benchmark superiority**: Significantly outperforms AutoGen and LangChain in multi-step tasks

### What CrawlForge Can Learn From It
- ReAct pattern for crawl decision-making (observe page → reason → act)
- "Timely abandonment" to avoid infinite loops on stuck crawls
- Shared memory for coordinating multiple crawler agents
- MCP integration for extensible tools

### Integration Possibility
**Very High** — ReAct pattern fits CrawlForge's crawl loop perfectly; MCP support would enable rich tool integrations.

---

### bolt-foundry/gambit (⭐224)
**URL:** https://github.com/bolt-foundry/gambit

### Description
Agent harness framework for building, running, and verifying LLM workflows.

### Key Technical Insights
- Workflow verification and testing
- LLM-centric task execution
- Observability for LLM-based agents

### What CrawlForge Can Learn From It
- Verification patterns for crawl workflows
- Testing frameworks for automated browsing

### Integration Possibility
**Medium** — Verification patterns could improve CrawlForge's reliability.

---

### dralgorhythm/claude-agentic-framework (⭐56)
**URL:** https://github.com/dralgorhythm/claude-agentic-framework

### Description
"A More Effective Agent Harness for Claude."

### Key Technical Insights
- Claude-specific optimizations
- Enhanced tool use and reasoning

### What CrawlForge Can Learn From It
- Claude-specific prompt engineering for browser tasks

### Integration Possibility
**Medium** — Could inform Claude integration patterns.

---

## Key Patterns Summary

### For CrawlForge Integration

| Pattern | Source | Applicability |
|---------|--------|---------------|
| **ReAct loop** | Autono | Core crawl decision-making |
| **Checkpoint/recovery** | Hive | Long job resilience |
| **Template matching** | bombcrypto-bot | Visual fallback for canvas/WebGL |
| **Self-healing agents** | Hive | Website change adaptation |
| **Multi-agent coordination** | PantheonOS, Autono | Distributed crawling |
| **MCP protocol** | Autono | Tool extensibility |
| **Human-in-the-loop** | Hive | Approval workflows |
| **Evolutionary improvement** | PantheonOS | Strategy optimization |

### Priority Integrations

1. **Autono (ReAct + MCP)** — Most relevant architecture for CrawlForge's core loop
2. **Hive (production harness)** — Checkpoint, recovery, observability for enterprise use
3. **bombcrypto-bot patterns** — Visual fallback adapter for non-DOM games

---

## Other Notable Projects

### lobehub/lobehub (⭐74,649)
Large AI agent platform with hub features.

### bytedance/deer-flow (⭐56,555)
"Open-source long-horizon SuperAgent harness" - research, code, creation with sandboxes, memories, tools, skills.

### code-yeongyu/oh-my-openagent (⭐46,959)
"omo; the best agent harness"

### langchain-ai/deepagents (⭐18,769)
Agent harness built with LangChain and LangGraph.

---

## ATX Project (Historical Reference)

**Note:** The original ATX project (openatx/atx - smartphone automation) appears to be archived/inactive. It pioneered Python-based mobile automation using uiautomator2, but development has moved to other projects.

For CrawlForge, if mobile game support is needed, consider `uiautomator2` or `Appium` directly.

---

*End of Landscape Report*
