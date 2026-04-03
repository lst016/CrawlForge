# Examples

Runnable demonstrations of CrawlForge's core capabilities.

## Demos

### `slot_machine_demo.py`

Complete walkthrough of slot game automation:

1. **SlotGameAdapter creation** — with custom config
2. **Session management** — start/end session
3. **ReAct loop simulation** — detect → action → extract (10 spins)
4. **DataCollector** — record spin-by-spin data
5. **CheckpointManager** — save/restore state
6. **DataExporter** — JSON + CSV export

Run:
```bash
python examples/slot_machine_demo.py
```

### `full_demo.py`

Full framework demo covering all major modules:

1. **AdapterRegistry** — register multiple adapters
2. **Adapter factory** — `registry.create()`
3. **Session lifecycle** — start → loop → end
4. **Checkpoint save/restore** — multiple checkpoints
5. **Data collection + export** — JSON, CSV
6. **AlgorithmAnalyzer** — RTP, volatility, win patterns
7. **Adapter capabilities** — introspection

Run:
```bash
python examples/full_demo.py
```

## Notes

- Both demos use **mocked runtimes** — no real ADB/Playwright needed
- Exports go to `/tmp/crawlforge_demo_*` directories
- Checkpoints go to `/tmp/crawlforge_demo_checkpoints`
- Real usage requires a real `ADBRuntime` or `PlaywrightRuntime`
