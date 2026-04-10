# Source Code Analysis

A small collection of **standalone Python 3** command-line tools for **static analysis** of multi-language codebases. There are no third-party dependencies—only the standard library—so you can copy the scripts into a repo or run them against any checkout.

The main tools are:

| Tool | Purpose |
|------|---------|
| [`complexity_analysis.py`](complexity_analysis.py) | Measures **structural complexity** (cyclomatic and cognitive complexity, nesting, lines of code, and a simple health score). |
| [`logging_analysis.py`](logging_analysis.py) | Measures **logging and diagnostic output**—how dense logging is, which APIs and levels are used, and where the hotspots are. |
| [`analyze_commits.py`](analyze_commits.py) | Summarizes **Git commit history** (churn, authors, categories, trends) from `git log` or a saved export. |

**`complexity_analysis.py`** and **`logging_analysis.py`** walk a directory tree, respect the same **exclude** rules, skip common build/vendor folders by default, and support **plain text** or **JSON** output. **`analyze_commits.py`** works on a repository path (or a pre-exported log) and prints a report plus a JSON summary file.

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

## `analyze_commits.py`

### What it does

`analyze_commits.py` parses **`git log --numstat --no-merges`** output (either by running Git in a repository, or by reading a file you saved earlier). It prints a **text report** and writes **`commit_analysis_results.json`** in the **current working directory** (where you run the command).

The report includes:

- **Hotspots**: files most often touched by commits, and files with the largest add/delete churn.
- **Commit categories** (heuristic): feature vs bug fix vs refactoring vs other, with examples.
- **Authors**: who has the most commits.
- **Timeline**: commits and line churn by year; bug vs feature counts by month.
- **Modules**: inferred from file paths (top-level path segment), with bug/feature counts per module.
- **Code age** (optional): table of **what share of today’s lines** (at `HEAD`) fall into time buckets by **last file change**. The **granularity** depends on how long the **repository history** is (oldest commit → now): **under ~6 months** → **ISO week**; **6 months to under 2 years** → **calendar month** (`YYYY-MM`); **2 years or more** → **years since last change** with buckets from 0–1y through 23–24y, then **24+ years**. This uses the **latest commit date per file** (not per-line `git blame`). After the table, you can list the **top N modules** (directory path without filename) **per bucket** by lines in that bucket, via **`--code-age-top-modules N`** (default **5**; use **0** to disable). Use **`--no-code-age`** to skip this step on huge repos (it runs `git ls-files` and `git show` per file).

Use **`--exclude`** to drop path prefixes from stats (for example generated or vendor trees). Excludes apply to the code-age scan as well.

### Prerequisites

- **Python 3.6+** (stdlib only).
- **Git** on `PATH` when you are **not** using `--commit-history` (the script runs `git` as a subprocess in the chosen repo).

### How to use it

| Argument / option | Short | Meaning |
|-------------------|-------|---------|
| `PATH` | (positional) | Root of the Git repo to analyze. Default: **`.`** (used as `cwd` for `git log`). |
| `--commit-history FILE` | `-H` | Read history from **FILE** (same format as `git log --numstat --no-merges`) instead of running Git. |
| `--export-commit-history [FILE]` | `-E` | After fetching from Git, write the raw log to **FILE**. Default file name: **`commit-history.txt`**. Cannot be combined with `-H`. |
| `--exclude …` | | Path prefixes to skip (for example `vendor/` `node_modules/`). |
| `--no-code-age` | | Skip the **code-age** table (faster on very large repositories). |
| `--code-age-top-modules N` | | Per code-age bucket, show the top **N** modules by lines in that bucket (default **5**; **0** = off). |

Examples:

```bash
python3 analyze_commits.py
python3 analyze_commits.py /path/to/repo
python3 analyze_commits.py . --exclude vendor/ node_modules/
python3 analyze_commits.py --export-commit-history
python3 analyze_commits.py ./myrepo -E /tmp/history.txt
python3 analyze_commits.py -H commit-history.txt
```

---

## Typical workflow

1. Run **`complexity_analysis.py`** on a service or monorepo folder to find **high-complexity** areas and track **LOC** and **nesting**.
2. Run **`logging_analysis.py`** on the same tree to see whether logging is **balanced** (density, levels, frameworks) and where **log-heavy** files are.
3. Optionally run **`analyze_commits.py`** on the **Git** checkout to see **churn**, **ownership**, and **change patterns** over time.

The first two can be run in **CI** with `--json` and thresholds enforced by your own scripts. **`analyze_commits.py`** needs a Git repo (or a saved log file) and writes `commit_analysis_results.json` for further processing.
