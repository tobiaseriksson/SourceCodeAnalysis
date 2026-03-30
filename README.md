# Source Code Analysis

A small collection of **standalone Python 3** command-line tools for **static analysis** of multi-language codebases. There are no third-party dependencies—only the standard library—so you can copy the scripts into a repo or run them against any checkout.

The two tools are:

| Tool | Purpose |
|------|---------|
| [`complexity_analysis.py`](complexity_analysis.py) | Measures **structural complexity** (cyclomatic and cognitive complexity, nesting, lines of code, and a simple health score). |
| [`logging_analysis.py`](logging_analysis.py) | Measures **logging and diagnostic output**—how dense logging is, which APIs and levels are used, and where the hotspots are. |

Both tools walk a directory tree, respect the same **exclude** rules, skip common build/vendor folders by default, and support **plain text** or **JSON** output for use in reviews or automation.

---

## Requirements

- **Python 3.6+**

Install nothing else; the scripts use only the standard library.

---

## `complexity_analysis.py`

### What it does

`complexity_analysis.py` analyzes source files and computes **per-file** and **project-wide** metrics:

- **Cyclomatic complexity** (McCabe)—branching structure of the code.
- **Cognitive complexity** (SonarSource-style)—how hard the control flow is to follow.
- **Lines**: total, code, comments, and blank lines.
- **Maximum nesting depth** and **function counts** (with optional per-function detail when verbose).
- An **overall health score** on a 1–5 scale.

### Supported languages (`complexity_analysis.py`)

Files are selected by extension. The script analyzes:

| Language | Typical extensions |
|----------|-------------------|
| JavaScript / TypeScript | `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs` |
| C# | `.cs` |
| Java | `.java` |
| C | `.c`, `.h` |
| C++ | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hxx` |
| Go | `.go` |
| Rust | `.rs` |
| Kotlin | `.kt`, `.kts` |
| PHP | `.php` |
| Swift | `.swift` |
| Ruby | `.rb` |
| R | `.r` |
| Dart | `.dart` |
| Scala | `.scala`, `.sc` |
| Python | `.py` |
| HTML / Razor (markup in templates) | `.html`, `.htm`, `.cshtml`, `.razor` |

The analyzer automatically skips typical noise paths (for example `node_modules`, `.git`, `dist`, `build`, `vendor`) and common generated files (for example `*.min.js`, `*.d.ts`, `*.Designer.cs`).

### How to use it

Run from a shell, optionally passing a **root directory** (default: current directory):

```bash
python3 complexity_analysis.py
python3 complexity_analysis.py ./src
```

**Useful options:**

| Option | Short | Meaning |
|--------|-------|---------|
| `--verbose` | `-v` | Print a **per-file** table (cyclomatic, cognitive, nesting, functions, lines). |
| `--top N` | `-t N` | Show the top **N** hotspot files/functions (default: **10**). |
| `--json` | `-j` | Emit **JSON** for scripts, CI, or other tools. |
| `--exclude …` | `-e …` | One or more **exclude patterns**: directories (`old/`), dir names, extensions (`.min.js`), exact filenames, or glob/subpath patterns. |

Examples:

```bash
python3 complexity_analysis.py . --verbose
python3 complexity_analysis.py ./backend --top 20
python3 complexity_analysis.py . --json
python3 complexity_analysis.py . --exclude old/ docs/ '*/test/*' '**/*.spec.ts'
```

### Tests

Unit tests live in [`test_complexity_analysis.py`](test_complexity_analysis.py). Run:

```bash
python3 -m unittest test_complexity_analysis -v
```

---

## `logging_analysis.py`

### What it does

`logging_analysis.py` scans source code for **real logging and print-style calls**, using language-specific patterns (for example `ILogger` / Serilog in C#, `console.log` in JS/TS, `logging.info` / `logger` in Python, `fmt.Println` in Go, and many others). It is designed to **avoid naive false positives** from words like “log” inside identifiers when possible.

For the codebase it reports:

- **Overview**: files analyzed, share of files with logging, code lines, **active** vs **commented-out** log lines, and **log density** (roughly how many code lines per log line).
- **Breakdowns** by **log level** (info, warn, error, debug, trace, …), by **framework/API**, and by **language** (where applicable).
- **Top files** with the most logging lines—useful for finding noisy modules or candidates for cleanup.

### Supported languages (`logging_analysis.py`)

Logging patterns are applied per language. The script scans **source** files with these extensions (it does **not** include HTML/Razor template files):

| Language | Typical extensions |
|----------|-------------------|
| JavaScript / TypeScript | `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs` |
| C# | `.cs` |
| Java | `.java` |
| Python | `.py` |
| C | `.c`, `.h` |
| C++ | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hxx` |
| Go | `.go` |
| Rust | `.rs` |
| Kotlin | `.kt`, `.kts` |
| PHP | `.php` |
| Swift | `.swift` |
| Ruby | `.rb` |
| R | `.r` |
| Dart | `.dart` |
| Scala | `.scala`, `.sc` |

Per-language **API patterns** (for example Serilog vs `console.log` vs `logging.info`) are listed in the docstring at the top of [`logging_analysis.py`](logging_analysis.py).

Like the complexity tool, it skips the same kinds of directories and generated files by default.

### How to use it

Syntax and flags match `complexity_analysis.py`:

```bash
python3 logging_analysis.py
python3 logging_analysis.py ./backend
python3 logging_analysis.py ./frontend --verbose
python3 logging_analysis.py . --json
python3 logging_analysis.py . --top 20 --exclude node_modules/ '**/*.spec.ts'
```

Use **`--verbose`** for the full per-file table and **`--json`** when you need machine-readable output.

---

## Typical workflow

1. Run **`complexity_analysis.py`** on a service or monorepo folder to find **high-complexity** areas and track **LOC** and **nesting**.
2. Run **`logging_analysis.py`** on the same tree to see whether logging is **balanced** (density, levels, frameworks) and where **log-heavy** files are.

Both can be run in **CI** with `--json` and thresholds enforced by your own scripts.
