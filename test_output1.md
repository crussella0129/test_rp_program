# Test Output 1 — Red Planet Integration Test Session

**Date:** 2026-03-10
**Branch:** `animus/red-planet` (Animus) + `main` (test_rp_program)
**Model:** Qwen2.5-Coder-14B-Instruct-Q4_K_M (local, llama-cpp-python)
**Agent:** Claude Opus 4.6 orchestrating Animus via subprocess

---

## Context

This document records the end-to-end test session for the Red Planet (Ferric Layer) update to Animus. The `test_rp_program` repository was created specifically to exercise the three new features from the `animus/red-planet` branch:

1. **`--no-plan` flag** — bypass the planner for targeted tasks
2. **`write_file` JSON unescaping** — preserve triple-quoted docstrings through the LLM JSON round-trip
3. **`ferric-parse`** — Rust-based multi-language code parser via tree-sitter

---

## Test 1: `--no-plan` Flag Verification

**Command:** `python -m src.main rise --help`

**Result:** PASSED

```
--no-plan     Bypass planner -- use agent loop directly for targeted tasks
```

The flag appears in the help output. When invoked with `--no-plan`, the agent loop runs directly without the `TaskDecomposer` / `PlanExecutor` pipeline. This was verified by the `test_no_plan_flag()` function in `test_rise.py`.

**Timing:** ~2 seconds (help output only, no model load)

---

## Test 2: write_file JSON Unescaping

**Command:** `echo "<task>" | python -m src.main rise --no-plan`

**Task given to Animus:**
> Write backend/analyzer.py. It must define one function: analyze(readings) with a docstring that says what it does, returning a dict with min, max, and mean of the readings list. Nothing else in the file.

**Result:** PASSED (second attempt)

### First Attempt (failed — timeout at 240s)
The model loaded and began generating but exceeded the 240-second timeout. The file was partially written. The model generated a more complex version than requested (with argparse and `if __name__` block), suggesting the 14B model interprets "nothing else in the file" loosely.

### Second Attempt (passed — timeout increased to 480s)
With the simplified task prompt and increased timeout, the model produced:

```python
def analyze(readings):
    """
    Analyzes a list of readings and returns a dictionary containing
    the minimum, maximum, and mean values.
    """
    if not readings:
        return {'min': None, 'max': None, 'mean': None}
    min_val = min(readings)
    max_val = max(readings)
    mean_val = sum(readings) / len(readings)
    return {'min': min_val, 'max': max_val, 'mean': mean_val}
```

**Key observations:**
- Triple-quoted docstring `"""..."""` preserved correctly on disk (not `\"\"\"`)
- File is valid Python (`ast.parse` check passed)
- Model added null-safety for empty list (not requested but reasonable)
- File size: 394 bytes

**Timing:** ~180-240 seconds (model load + inference + tool call + verification loop)

---

## Test 3: ferric-parse on Generated Code

**Command:** `ferric-parse.exe backend/analyzer.py`

**Result:** PASSED

```json
{
    "file_path": "backend/analyzer.py",
    "nodes": [
        {
            "kind": "function",
            "name": "analyze",
            "qualified_name": "analyzer.analyze",
            "line_start": 1,
            "line_end": 10,
            "docstring": "Analyzes a list of readings and returns a dictionary containing the minimum, maximum, and mean values."
        }
    ],
    "edges": []
}
```

**Key observations:**
- `kind="function"` correctly identified (not "method" — it is module-level)
- `qualified_name` follows the `module.function` convention
- `docstring` extracted from the triple-quoted string
- Empty `edges` is expected for a single standalone function

**Timing:** <100ms (Rust binary, no model involved)

---

## Playwright End-to-End Tests

**Command:** `pytest tests/test_frontend.py -v --browser chromium`

**Result:** 11/11 PASSED in 11.91 seconds

```
test_health_dot_turns_green[chromium]          PASSED
test_health_message_shows_mission[chromium]     PASSED
test_analyze_shows_results_panel[chromium]      PASSED
test_analyze_count[chromium]                    PASSED
test_analyze_mean[chromium]                     PASSED
test_analyze_min_max[chromium]                  PASSED
test_analyze_single_reading[chromium]           PASSED
test_empty_input_shows_error[chromium]          PASSED
test_non_numeric_input_shows_error[chromium]    PASSED
test_results_hidden_before_submit[chromium]     PASSED
test_button_re_enables_after_response[chromium] PASSED
```

### Screenshots Captured

| Screenshot | Description |
|-----------|-------------|
| `screenshots/01_initial_load.png` | Dashboard on first load — green health dot, empty textarea |
| `screenshots/02_analysis_results.png` | After submitting 7 readings — stats panel visible |
| `screenshots/03_error_empty.png` | Error message when clicking Analyze with no input |

---

## API Direct Tests (curl)

```bash
# Health check
$ curl http://localhost:8765/api/health
{"status":"ok","mission":"Red Planet"}

# Valid stats request
$ curl -X POST http://localhost:8765/api/stats \
  -H "Content-Type: application/json" \
  -d '{"readings": [23.1, 45.7, 18.3, 67.2, 34.8, 89.0, 56.4]}'
{"count":7,"mean":47.7857,"median":45.7,"std_dev":25.1711,"min":18.3,"max":89.0}

# Empty readings (validation)
$ curl -X POST http://localhost:8765/api/stats \
  -H "Content-Type: application/json" \
  -d '{"readings": []}'
{"detail":"readings must not be empty"}
```

---

## ferric-parse on Repository Code

### backend/main.py
- **Nodes found:** 4 (1 class `ReadingsRequest`, 3 functions `index`, `health`, `compute_stats`)
- **Docstrings extracted:** "Liveness check." and "Compute descriptive statistics over telemetry readings."
- `ReadingsRequest` identified with base class `BaseModel`

### backend/telemetry.py
- **Nodes found:** 9 (1 class `TelemetryStats`, 8 methods including `__init__`, `count`, `mean`, `median`, `std_dev`, `minimum`, `maximum`, `summary`)
- Methods correctly identified as `kind="method"` with qualified names like `telemetry.TelemetryStats.mean`
- Class docstring: "Descriptive statistics over a list of telemetry readings."

---

## Issues Encountered During Session

### 1. Windows cp1252 Encoding vs. Unicode Art
**Problem:** Animus's ASCII art banner uses Unicode characters that crash Python's subprocess reader on Windows.
**Fix:** Added `encoding="utf-8"` and `errors="replace"` to all `subprocess.run()` calls, plus `PYTHONIOENCODING=utf-8` in the environment.

### 2. Model Timeout on First Invocation
**Problem:** First `test_rise.py` run timed out at 180s because the 14B GGUF model takes ~30s to load and ~150-200s for inference + tool execution.
**Fix:** Increased timeout to 480s and simplified the task prompt to reduce token generation.

### 3. Model Instruction-Following Fidelity
**Problem:** First attempt produced a file with argparse, `__main__` block, and a string-return function instead of the requested dict-return function with just a docstring.
**Fix:** Simplified the task to a shorter, more direct prompt. Second attempt was much closer to spec.

### 4. JavaScript Float Rendering
**Problem:** Backend returns `20.0` as JSON float, but JavaScript's `JSON.parse` converts to `20` (drops `.0`), causing Playwright assertions expecting `"20.0"` to fail.
**Fix:** Updated test assertions to check for `"20"` instead of `"20.0"`.

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| `--no-plan` flag | Working | Immediate bypass, fast response |
| `write_file` unescaping | Working | `"""` preserved, valid Python output |
| `ferric-parse` binary | Working | <100ms, correct kind/docstring extraction |
| FastAPI backend | Working | Health, stats, validation all correct |
| Frontend dashboard | Working | 11/11 Playwright tests pass |
| Animus integration | Working with caveats | Requires 480s timeout, simplified prompts |
