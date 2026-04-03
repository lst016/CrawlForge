# Benchmarks

Performance benchmarks for CrawlForge core components.

## Running

```bash
python benchmarks/run_benchmark.py
```

## Benchmark Categories

| Component | What it tests |
|-----------|--------------|
| **CheckpointManager** | `save`, `load`, `load_state` throughput |
| **PriorityQueue** | `push`, `push+pop` throughput |
| **DataExporter** | JSON, CSV, Parquet export of 1000 rows |
| **AdapterRegistry** | `get` lookup and `create` factory ops |
| **Memory** | Peak memory for 50 checkpoint saves |

## Output

- Console: formatted table of operations/second and peak memory
- JSON: `~/.crawlforge/benchmark_results.json`

## Sample Output

```
======================================================================
CrawlForge Performance Benchmarks
======================================================================
  Python: 3.9.6
  Date:   2026-04-03

======================================================================
CheckpointManager Benchmarks
======================================================================
  Operation                           Time       Throughput
----------------------------------------------------------------------
  CheckpointManager.save (100 ops)  196.21 ms    509.67 ops/s
  CheckpointManager.load (1000 ops)   1.90 ms  525348.04 ops/s
  CheckpointManager.load_state      1.53 ms   654468.25 ops/s

======================================================================
PriorityQueue Benchmarks
======================================================================
  PriorityQueue.push (10000 ops)    105.97 ms   94363.88 ops/s
  PriorityQueue.push+pop            108.01 ms   92584.95 ops/s

======================================================================
DataExporter (1000 records)
======================================================================
  JSON                               469 µs      2131.63 ops/s
  CSV                                271 µs      3678.72 ops/s
  Parquet                          221.44 ms       4.52 ops/s

======================================================================
AdapterRegistry
======================================================================
  get (1000 lookups)               328 µs    3045298 ops/s
  create (100 ops)                   1.2 ms   83289 ops/s
```

## Notes

- Benchmarks use temporary directories for isolation
- GC is collected before each benchmark for accurate timing
- Memory is measured via `tracemalloc`
- Parquet export falls back to JSON if pandas/pyarrow unavailable
