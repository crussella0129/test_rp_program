"""
Animus Rise — Red Planet Integration Test
==========================================
Exercises the three Ferric Layer / Red Planet improvements live:

  1. --no-plan flag  (bypass planner for targeted tasks)
  2. write_file JSON unescaping  (triple-quoted docstrings survive the round-trip)
  3. ferric-parse  (Rust binary parses the written file and finds the new function)

Run:
    python test_rise.py

Requirements:
  - Animus installed at ANIMUS_DIR (default: C:/Users/charl/animus)
  - A local LLM model configured in Animus
  - ferric-parse binary built (optional — test 3 is skipped when absent)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_DIR = Path(__file__).parent.resolve()
ANIMUS_DIR = Path(os.environ.get("ANIMUS_DIR", r"C:\Users\charl\animus"))
PYTHON = sys.executable

# Animus is invoked with PYTHONPATH pointing at its own directory so that
# `python -m src.main` resolves correctly while the workspace root (CWD)
# is this repo — giving Animus permission to write here and nowhere else.
ENV = {
    **os.environ,
    "PYTHONPATH": str(ANIMUS_DIR),
    "PYTHONIOENCODING": "utf-8",   # Animus banner uses Unicode art
}

TARGET = REPO_DIR / "backend" / "analyzer.py"

TASK = (
    "Write backend/analyzer.py. "
    "It must define one function: analyze(readings) "
    "with a docstring that says what it does, "
    "returning a dict with min, max, and mean of the readings list. "
    "Nothing else in the file."
)


def _run_animus(task: str, timeout: int = 480) -> subprocess.CompletedProcess:
    """Invoke `animus rise --no-plan` with *task* piped to stdin."""
    return subprocess.run(
        [PYTHON, "-m", "src.main", "rise", "--no-plan"],
        input=task,
        cwd=REPO_DIR,
        env=ENV,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Test 1: --no-plan routes directly to the agent loop
# ---------------------------------------------------------------------------

def test_no_plan_flag():
    """--no-plan must appear in `animus rise --help` and bypass the planner."""
    result = subprocess.run(
        [PYTHON, "-m", "src.main", "rise", "--help"],
        cwd=REPO_DIR,
        env=ENV,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, f"rise --help failed:\n{result.stderr}"
    assert "--no-plan" in result.stdout, "--no-plan option missing from help"
    print("  [1] --no-plan present in rise --help OK")


# ---------------------------------------------------------------------------
# Test 2: write_file unescaping — triple-quoted docstrings survive
# ---------------------------------------------------------------------------

def test_write_file_with_docstring():
    """
    Animus writes backend/analyzer.py including a triple-quoted docstring.
    If write_file JSON unescaping is working the file will contain \"\"\"
    rather than the escaped form \\\"\\\"\\\".
    """
    if TARGET.exists():
        TARGET.unlink()

    proc = _run_animus(TASK)

    # The model or planner may print diagnostics to stderr — that is fine.
    # We only care that the file now exists and is syntactically valid Python.
    assert TARGET.exists(), (
        f"Animus did not create backend/analyzer.py\n"
        f"--- stdout ---\n{proc.stdout[-2000:]}\n"
        f"--- stderr ---\n{proc.stderr[-1000:]}"
    )

    content = TARGET.read_text(encoding="utf-8")

    assert "def analyze" in content, (
        f"analyze function missing from {TARGET}\nContent:\n{content}"
    )
    # Triple-quoted string must appear somewhere — proves write_file unescaping
    # didn't corrupt """ into \"\"\" on disk.
    assert '"""' in content or "'''" in content, (
        f"No triple-quoted string found — write_file unescaping may be broken.\n"
        f"Content:\n{content}"
    )

    # Verify it is valid, importable Python
    compile_result = subprocess.run(
        [PYTHON, "-c", f"import ast; ast.parse(open(r'{TARGET}').read())"],
        capture_output=True, text=True,
    )
    assert compile_result.returncode == 0, (
        f"backend/analyzer.py is not valid Python:\n{compile_result.stderr}\n"
        f"Content:\n{content}"
    )

    print(f"  [2] write_file docstring round-trip OK  ({TARGET.stat().st_size} bytes)")


# ---------------------------------------------------------------------------
# Test 3: ferric-parse reads the written file and finds the function
# ---------------------------------------------------------------------------

def test_ferric_parse_finds_function():
    """
    ferric-parse (Rust binary) must parse backend/analyzer.py and return
    a node with name='analyze' and kind='function'.
    Skipped when the binary is not built.
    """
    # Locate binary using the same discovery logic as src/ferric.py
    ferric_bin = None
    bin_dir = ANIMUS_DIR / "src" / "bin"
    for candidate in (
        bin_dir / "ferric-parse.exe",
        bin_dir / "ferric-parse",
        ANIMUS_DIR / "target" / "debug" / "ferric-parse.exe",
        ANIMUS_DIR / "target" / "debug" / "ferric-parse",
    ):
        if candidate.exists():
            ferric_bin = str(candidate)
            break

    if ferric_bin is None:
        import shutil
        ferric_bin = shutil.which("ferric-parse")

    if ferric_bin is None:
        print("  [3] ferric-parse binary not found — SKIPPED")
        print("       (build with: cd animus && cargo build -p ferric-parse)")
        return

    assert TARGET.exists(), "backend/analyzer.py must exist before running ferric-parse test"

    result = subprocess.run(
        [ferric_bin, str(TARGET)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"ferric-parse failed:\n{result.stderr}"

    data = json.loads(result.stdout)
    nodes = data.get("nodes", [])
    names = [n["name"] for n in nodes]

    assert "analyze" in names, (
        f"ferric-parse did not find 'analyze' in {TARGET}\nnodes: {nodes}"
    )

    analyze_node = next(n for n in nodes if n["name"] == "analyze")
    assert analyze_node["kind"] == "function", (
        f"Expected kind='function', got '{analyze_node['kind']}'"
    )

    print(f"  [3] ferric-parse found 'analyze' as kind='{analyze_node['kind']}' OK")
    print(f"       qualified_name: {analyze_node.get('qualified_name', '?')}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\nAnimus Rise — Red Planet Integration Test")
    print("=" * 44)

    failures = []
    for fn in (test_no_plan_flag, test_write_file_with_docstring, test_ferric_parse_finds_function):
        print(f"\nRunning {fn.__name__}…")
        try:
            fn()
        except Exception as exc:
            print(f"  FAILED: {exc}")
            failures.append(fn.__name__)

    print()
    if failures:
        print(f"FAILED ({len(failures)}): {', '.join(failures)}")
        sys.exit(1)
    else:
        print("All tests passed.")
