#!/usr/bin/env python3
"""
Code Complexity Analyzer — Multi-language (15 languages).

Supported languages:
  - TypeScript / TSX / JavaScript (including .mjs, .cjs)
  - C# (.cs)
  - Java (.java)
  - C (.c, .h)
  - C++ (.cpp, .cc, .cxx, .hpp, .hxx)
  - Go (.go)
  - Rust (.rs)
  - Kotlin (.kt, .kts)
  - PHP (.php)
  - Swift (.swift)
  - Ruby (.rb)
  - R (.r, .R)
  - Dart (.dart)
  - Scala (.scala, .sc)
  - HTML (.html, .htm, .cshtml, .razor)

Calculates per-file and project-wide:
  - Cyclomatic Complexity  (McCabe, 1976)
  - Cognitive Complexity   (SonarSource, 2023)
  - Lines of code, comments, blanks
  - Nesting depth
  - Overall health score   (1–5)

Prerequisites:
  - Python 3.6+ (no external dependencies)

How to run:
  From the project root, execute one of the following commands:

    # Analyze the current directory (default)
    python3 complexity_analysis.py

    # Analyze a specific directory
    python3 complexity_analysis.py ./backend

    # Analyze with per-file detail table (verbose)
    python3 complexity_analysis.py ./backend --verbose
    python3 complexity_analysis.py ./backend -v

    # Show top N hotspot files (default: 10)
    python3 complexity_analysis.py ./backend --top 20
    python3 complexity_analysis.py ./backend -t 20

    # Output results as JSON (for CI/tooling integration)
    python3 complexity_analysis.py ./backend --json
    python3 complexity_analysis.py ./backend -j

    # Exclude files, directories, extensions, or glob patterns
    python3 complexity_analysis.py ./backend --exclude old/
    python3 complexity_analysis.py ./backend --exclude old/ docs/
    python3 complexity_analysis.py ./backend -e .min.js .d.ts
    python3 complexity_analysis.py ./backend --exclude HeromaImport.cs
    python3 complexity_analysis.py ./backend --exclude '*/test/*'
    python3 complexity_analysis.py ./backend --exclude '**/*.spec.ts'

    # Combine flags
    python3 complexity_analysis.py ./backend --verbose --top 20 --exclude old/ docs/

  CLI arguments:
    directory            Directory to analyze (default: current directory)
    --verbose, -v        Show a per-file detail table with CC, Cog, Nest, Fns, Lines
    --top N, -t N        Number of hotspot files/functions to display (default: 10)
    --json, -j           Output all metrics as JSON instead of the text report
    --exclude, -e PATTERN [PATTERN ...]
                         Exclude files/dirs matching one or more patterns:
                           • Directory:  old/  or  docs/     (trailing slash)
                           • Dir name:   old   or  docs      (matches anywhere)
                           • Extension:  .min.js  or  .d.ts  (leading dot)
                           • Filename:   HeromaImport.cs     (exact match)
                           • Glob:       '*/test/*'          (fnmatch pattern)
                           • Subpath:    src/app/plan         (substring match)

  The script automatically skips:
    - Directories: node_modules, .git, dist, build, bin, obj, vendor, etc.
    - Files:       *.d.ts, *.min.js, *.Designer.cs, etc.

Tests:
  Unit tests live in test_complexity_analysis.py (same directory).
  Run them with:
    python3 -m unittest test_complexity_analysis -v
"""

import os
import re
import sys
import json
import fnmatch
import argparse
from pathlib import Path


# ─── Configuration ──────────────────────────────────────────────────────────

EXTENSIONS = {
    # TypeScript / JavaScript
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    # C#
    ".cs",
    # Java
    ".java",
    # C / C++
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx",
    # Go
    ".go",
    # Rust
    ".rs",
    # Kotlin
    ".kt", ".kts",
    # PHP
    ".php",
    # Swift
    ".swift",
    # Ruby
    ".rb",
    # R
    ".r",
    # Dart
    ".dart",
    # Scala
    ".scala", ".sc",
    # Python
    ".py",
    # HTML / Razor
    ".html", ".htm", ".cshtml", ".razor",
}
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt",
    ".lovable", ".gemini", ".vscode", ".idea", "coverage", "__pycache__",
    "bin", "obj", "target", "out", ".gradle", ".mvn", "packages",
    "vendor", "Pods", ".pub-cache",
}
SKIP_SUFFIXES = {".d.ts", ".min.js", ".bundle.js", ".Designer.cs", ".g.cs", ".g.i.cs"}

# Language families
LANG_JS = {"js", "jsx", "ts", "tsx", "mjs", "cjs"}
LANG_CSHARP = {"cs"}
LANG_JAVA = {"java"}
LANG_C = {"c", "h"}
LANG_CPP = {"cpp", "cc", "cxx", "hpp", "hxx"}
LANG_GO = {"go"}
LANG_RUST = {"rs"}
LANG_KOTLIN = {"kt", "kts"}
LANG_PHP = {"php"}
LANG_SWIFT = {"swift"}
LANG_RUBY = {"rb"}
LANG_R = {"r"}
LANG_DART = {"dart"}
LANG_SCALA = {"scala", "sc"}
LANG_PYTHON = {"py"}
LANG_HTML = {"html", "htm", "cshtml", "razor"}
# All languages that use C-style // and /* */ comments and brace-delimited blocks
LANG_CSTYLE = (LANG_JS | LANG_CSHARP | LANG_JAVA | LANG_C | LANG_CPP |
               LANG_GO | LANG_RUST | LANG_KOTLIN | LANG_SWIFT | LANG_DART |
               LANG_SCALA | LANG_PHP)

# Thresholds for *per-file* aggregate scores (whole-file CC/Cog sums).
#
# Cyclomatic (McCabe): widely used risk bands from the SEI / C4 Software Technology
# Reference Guide (Carnegie Mellon), summarized e.g. in JetBrains ReSharper cyclomatic
# plugin docs: 1–10 low, 11–20 moderate, 21–50 high. Above 50 is “very high risk” in that
# table; we split the tail into very high (51–100) and extreme (>100). The 100 boundary
# is a round second tier (double the “high” band width) used in many tooling reports.
# SonarQube S1541 defaults to 10 per method.
CC_LOW = 10
CC_MODERATE = 20
CC_HIGH = 50
CC_VERY_HIGH = 100

# Cognitive (SonarSource): rule S3776 defaults to threshold 15 *per method*; file totals
# use the same low/moderate/high edges as cyclomatic where possible; 51–100 vs >100
# mirrors the CC split for the upper tail.
COG_LOW = 15
COG_MODERATE = 25
COG_HIGH = 50
COG_VERY_HIGH = 100

# Max nesting depth (per file): brace / block depth reported by the analyzer.
# ESLint max-depth defaults to 4; Sonar S134-style rules flag deep control flow.
# Bands: shallow (0–2), near cap (3–4), deeper (5–6), very deep (7–9), extreme (10+).
NEST_LOW = 2
NEST_MODERATE = 4
NEST_HIGH = 6
NEST_VERY_HIGH = 9

# Functions per file (detected top-level units): no single industry standard; bands use
# the same numeric edges as cyclomatic/cognitive for consistency. Rough intent: few
# units per file (low), typical modules (moderate), crowded files (high), very large
# modules (very high), “god files” (extreme).
FN_LOW = 10
FN_MODERATE = 25
FN_HIGH = 50
FN_VERY_HIGH = 100


def _metrics_excluding_markup(metrics: list) -> list:
    """HTML, CSHTML, and Razor share lang 'html'; omit from code-complexity summaries."""
    return [m for m in metrics if m.lang != "html"]


# ─── Data classes ───────────────────────────────────────────────────────────

class FileMetrics:
    def __init__(self, path: str, lang: str = ""):
        self.path = path
        self.lang = lang            # e.g. "ts", "cs", "java", "html"
        self.total_lines = 0
        self.code_lines = 0
        self.comment_lines = 0
        self.blank_lines = 0
        self.cyclomatic = 1
        self.cognitive = 0
        self.max_nesting = 0
        self.functions = 0
        self.function_metrics = []  # List[FunctionMetrics]

    def to_dict(self):
        return {
            "path": self.path,
            "language": self.lang,
            "total_lines": self.total_lines,
            "code_lines": self.code_lines,
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
            "cyclomatic": self.cyclomatic,
            "cognitive": self.cognitive,
            "max_nesting": self.max_nesting,
            "functions": self.functions,
            "function_detail": [f.to_dict() for f in self.function_metrics],
        }


class FunctionMetrics:
    """Per-function complexity metrics."""
    def __init__(self, name: str, file_path: str, start_line: int):
        self.name = name
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = 0
        self.code_lines = 0
        self.cyclomatic = 1
        self.cognitive = 0
        self.max_nesting = 0

    @property
    def qualified_name(self):
        return f"{self.name}  ({self.file_path}:{self.start_line})"

    def to_dict(self):
        return {
            "name": self.name,
            "file": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "code_lines": self.code_lines,
            "cyclomatic": self.cyclomatic,
            "cognitive": self.cognitive,
            "max_nesting": self.max_nesting,
        }


# ─── Function/method detection patterns ────────────────────────────────────

# C#: method declarations (access modifier + return type + name + parens)
_FUNC_CS = re.compile(
    r"^\s*(?:public|private|protected|internal|static|virtual|override|abstract|async|sealed|partial|new|extern|\s)*"
    r"\s+(?:\w[\w<>\[\],\s\?]*\s+)?\w+\s*\("
    r"(?!.*;\s*$)"   # exclude interface method declarations (end with ;)
)
# JS/TS: function declarations, arrow functions, class methods
_FUNC_JS = re.compile(
    r"(?:"
    r"\bfunction\s+\w+\s*\(|"                          # function name(
    r"\bfunction\s*\(|"                                 # function(
    r"(?:async\s+)?\w+\s*\([^)]*\)\s*(?::\s*\w[\w<>|&\[\]]*)?\s*\{|"  # method(args) {
    r"(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\([^)]*\)\s*=>"     # const x = (...) =>
    r")",
)
# Java: method declarations
_FUNC_JAVA = re.compile(
    r"^\s*(?:public|private|protected|static|final|abstract|synchronized|native|\s)*"
    r"\s+\w[\w<>\[\],\s\?]*\s+\w+\s*\(",
)
# C/C++: function definitions (return type + name + parens + opening brace nearby)
_FUNC_C = re.compile(
    r"^\s*(?:static\s+|inline\s+|extern\s+|const\s+)*"
    r"\w[\w\s\*]*\s+\*?\w+\s*\(",
)
# Go: func declarations
_FUNC_GO = re.compile(
    r"^\s*func\s+(?:\([^)]*\)\s+)?\w+\s*\(",
)
# Rust: fn declarations
_FUNC_RUST = re.compile(
    r"^\s*(?:pub(?:\s*\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+\w+",
)
# Kotlin: fun declarations
_FUNC_KOTLIN = re.compile(
    r"^\s*(?:public|private|protected|internal|override|open|abstract|inline|suspend|\s)*"
    r"\s*fun\s+(?:<[^>]+>\s+)?\w+\s*\(",
)
# PHP: function declarations
_FUNC_PHP = re.compile(
    r"^\s*(?:public|private|protected|static|abstract|final|\s)*"
    r"\s*function\s+\w+\s*\(",
)
# Swift: func declarations
_FUNC_SWIFT = re.compile(
    r"^\s*(?:public|private|internal|fileprivate|open|override|static|class|\s)*"
    r"\s*func\s+\w+",
)
# Ruby: def declarations
_FUNC_RUBY = re.compile(
    r"^\s*def\s+(?:self\.)?\w+",
)
# Python: def declarations
_FUNC_PYTHON = re.compile(
    r"^\s*(?:async\s+)?def\s+\w+\s*\(",
)
# R: function assignments (name <- function)
_FUNC_R = re.compile(
    r"^\s*\w+\s*(?:<-|=)\s*function\s*\(",
)
# Dart: function/method declarations
_FUNC_DART = re.compile(
    r"^\s*(?:static\s+|abstract\s+)?(?:\w[\w<>?]*\s+)?\w+\s*\([^)]*\)\s*(?:async\s*)?\{",
)
# Scala: def declarations
_FUNC_SCALA = re.compile(
    r"^\s*(?:override\s+)?(?:private|protected)?\s*def\s+\w+",
)


# ─── Complexity patterns per language ──────────────────────────────────────

def _get_lang(ext: str) -> str:
    """Map file extension (without dot) to a language key."""
    ext = ext.lower()
    if ext in LANG_JS:
        return "js"
    if ext in LANG_CSHARP:
        return "cs"
    if ext in LANG_JAVA:
        return "java"
    if ext in LANG_C:
        return "c"
    if ext in LANG_CPP:
        return "cpp"
    if ext in LANG_GO:
        return "go"
    if ext in LANG_RUST:
        return "rust"
    if ext in LANG_KOTLIN:
        return "kotlin"
    if ext in LANG_PHP:
        return "php"
    if ext in LANG_SWIFT:
        return "swift"
    if ext in LANG_RUBY:
        return "ruby"
    if ext in LANG_R:
        return "r"
    if ext in LANG_DART:
        return "dart"
    if ext in LANG_SCALA:
        return "scala"
    if ext in LANG_PYTHON:
        return "py"
    if ext in LANG_HTML:
        return "html"
    return "unknown"


# ── Shared C-style patterns (JS/TS, C#, Java) ──────────────────────────────
#
# Cyclomatic Complexity (McCabe, 1976):
#   CC = 1 + number of decision points in the code.
#   Decision points: if, else if, while, for, case, catch, &&, ||, ?:
#   Note: \bif\s*\( already matches the 'if' inside 'else if',
#   so 'else if' must NOT be listed separately (would double-count).
#
#   Language-specific CC notes:
#   - Python: `if` in `x if cond else y` is not a separate decision; ternary is one pattern.
#   - Rust: each `=>` arm in match counts (like C switch `case`), not the `match` keyword.
#   - Go: `for { ... }` (no parentheses) is counted as a loop decision.
#
# Cognitive Complexity (SonarSource, 2023):
#   Four increment categories (per the official white paper):
#
#   Structural (S): +1 + current_nesting_level
#     if, ternary (?:), for, while, do-while, foreach, switch, catch
#     NOTE: 'else if' is NOT structural — see Hybrid below.
#
#   Hybrid (H): +1 only (no nesting penalty)
#     else, else if / elif
#     These DO increase nesting level for their children.
#
#   Fundamental (F): +1 only (no nesting penalty)
#     Logical operator SEQUENCES (not per-occurrence):
#       a && b && c  →  +1  (one sequence of &&)
#       a && b || c  →  +2  (one && seq, one || seq)
#     Python `and`/`or` and Ruby `and`/`or` (merged with &&/|| in Ruby) follow the same rule.
#     goto, break-to-label, continue-to-label
#     Recursion (requires call-graph — not implemented here)
#
#   Ignored (score = 0):
#     try, finally, synchronized, null-coalescing (??, ?.)  
#     Simple return, break, continue
#     case labels (only switch itself is counted)
#
#   Nesting level increases for:
#     if, else, else if, ternary, switch, for, while, do-while,
#     foreach, catch, nested lambdas/functions (but lambdas get no
#     increment themselves — they only increase nesting).
#

_CC_COMMON = [
    re.compile(r"\bif\s*\("),          # matches both 'if' and 'else if'
    re.compile(r"\bwhile\s*\("),
    re.compile(r"\bfor\s*\("),
    re.compile(r"\bcase\s+"),
    re.compile(r"\bcatch\s*\("),
    re.compile(r"&&"),
    re.compile(r"\|\|"),
    re.compile(r"\?[^?.:]*:"),         # ternary  ?x:y
]

# Cognitive: structural patterns → +1 + nesting_level
# These also increase nesting for their children.
# NOTE: 'if' here must NOT match 'else if' — that's handled as hybrid.
_COG_STRUCT_COMMON = [
    re.compile(r"(?<!\belse\s)\bif\s*\("),   # standalone 'if' only (not 'else if')
    re.compile(r"\bwhile\s*\("),
    re.compile(r"\bfor\s*\("),
    re.compile(r"\bswitch\s*\("),
    re.compile(r"\bcatch\s*\("),              # catch is structural per spec
    re.compile(r"\?[^?.:]*:"),               # ternary operator is structural
]

# Cognitive: hybrid patterns → +1 only (no nesting penalty)
# These DO increase nesting level for their children.
_COG_HYBRID_COMMON = [
    re.compile(r"\belse\s+if\s*\("),          # else-if
    re.compile(r"\belse\b(?!\s+if)"),         # standalone else
]

# ── JavaScript / TypeScript extras ──────────────────────────────────────────

_CC_JS_EXTRA = [
    re.compile(r"\?\?(?!=)"),          # nullish coalescing
]
_COG_STRUCT_JS_EXTRA = []
_COG_HYBRID_JS_EXTRA = []

# ── C# extras ──────────────────────────────────────────────────────────────

_CC_CS_EXTRA = [
    re.compile(r"\bforeach\s*\("),
    re.compile(r"\?\?(?!=)"),          # null coalescing
    re.compile(r"\bwhen\s*\("),        # exception filter (C# 6+)
]

_COG_STRUCT_CS_EXTRA = [
    re.compile(r"\bforeach\s*\("),
]

_COG_HYBRID_CS_EXTRA = []

# ── Java extras ────────────────────────────────────────────────────────────

_CC_JAVA_EXTRA = []
_COG_STRUCT_JAVA_EXTRA = []
_COG_HYBRID_JAVA_EXTRA = []

# ── C/C++ extras ───────────────────────────────────────────────────────────

_CC_C_EXTRA = [
    re.compile(r"\bgoto\b"),
]
_COG_STRUCT_C_EXTRA = []
_COG_HYBRID_C_EXTRA = []

# ── Go extras ──────────────────────────────────────────────────────────────
# Go uses 'select' for channel operations and 'range' in for loops
_CC_GO_EXTRA = [
    re.compile(r"\bselect\s*\{"),
    re.compile(r"\bfor\s*\{"),  # for { } without C-style (...)
]
_COG_STRUCT_GO_EXTRA = [
    re.compile(r"\bselect\s*\{"),
    re.compile(r"\bfor\s*\{"),
]
# Go uses 'else if' like C-style
_COG_HYBRID_GO_EXTRA = []

# ── Rust extras ────────────────────────────────────────────────────────────
# Rust: count each match arm (=>) like C switch counts each case; not match keyword
_CC_RUST_EXTRA = [
    re.compile(r"\bloop\s*\{"),
    re.compile(r"=>"),
    re.compile(r"\bif\s+let\b"),
]
_COG_STRUCT_RUST_EXTRA = [
    re.compile(r"\bloop\s*\{"),
    re.compile(r"\bmatch\b"),
]
_COG_HYBRID_RUST_EXTRA = []

# ── Kotlin extras ──────────────────────────────────────────────────────────
_CC_KOTLIN_EXTRA = [
    re.compile(r"\bwhen\s*[({]"),     # when expression (like switch)
]
_COG_STRUCT_KOTLIN_EXTRA = [
    re.compile(r"\bwhen\s*[({]"),
]
_COG_HYBRID_KOTLIN_EXTRA = []

# ── PHP extras ─────────────────────────────────────────────────────────────
_CC_PHP_EXTRA = [
    re.compile(r"\bforeach\s*\("),
    re.compile(r"\belseif\s*\("),
]
_COG_STRUCT_PHP_EXTRA = [
    re.compile(r"\bforeach\s*\("),
]
_COG_HYBRID_PHP_EXTRA = [
    re.compile(r"\belseif\s*\("),
]

# ── Swift extras ───────────────────────────────────────────────────────────
_CC_SWIFT_EXTRA = [
    re.compile(r"\bguard\b"),
    re.compile(r"\brepeat\s*\{"),
]
_COG_STRUCT_SWIFT_EXTRA = [
    re.compile(r"\bguard\b"),
    re.compile(r"\brepeat\s*\{"),
]
_COG_HYBRID_SWIFT_EXTRA = []

# ── Dart extras ────────────────────────────────────────────────────────────
_CC_DART_EXTRA = [
    re.compile(r"\?\?(?!=)"),
]
_COG_STRUCT_DART_EXTRA = []
_COG_HYBRID_DART_EXTRA = []

# ── Scala extras ───────────────────────────────────────────────────────────
_CC_SCALA_EXTRA = [
    re.compile(r"\bmatch\s*\{"),
]
_COG_STRUCT_SCALA_EXTRA = [
    re.compile(r"\bmatch\s*\{"),
]
_COG_HYBRID_SCALA_EXTRA = []

# ── Python extras ──────────────────────────────────────────────────────────
# Python uses indentation, not braces, so CC patterns are different
_CC_PYTHON = [
    # Statement if — exclude middle `if` in `x if cond else y` (ternary counted below)
    re.compile(r"\bif\b(?!\s+.+\s+else)"),
    re.compile(r"\belif\b"),
    re.compile(r"\bwhile\b"),
    re.compile(r"\bfor\b"),
    re.compile(r"\bexcept\b"),
    re.compile(r"\band\b"),
    re.compile(r"\bor\b"),
    re.compile(r"\bif\s+.+\s+else\b"),  # conditional expression (ternary)
]
_COG_STRUCT_PYTHON = [
    re.compile(r"(?<!\bel)\bif\b(?!\s+.+\s+else)"),  # standalone if (not elif, not ternary)
    re.compile(r"\bwhile\b"),
    re.compile(r"\bfor\b"),
    re.compile(r"\bexcept\b"),
]
_COG_HYBRID_PYTHON = [
    re.compile(r"\belif\b"),
    re.compile(r"\belse\s*:"),
]

# ── Ruby extras ────────────────────────────────────────────────────────────
_CC_RUBY = [
    re.compile(r"\bif\b"),
    re.compile(r"\belsif\b"),
    re.compile(r"\bunless\b"),
    re.compile(r"\bwhile\b"),
    re.compile(r"\buntil\b"),
    re.compile(r"\bfor\b"),
    re.compile(r"\bwhen\b"),
    re.compile(r"\brescue\b"),
    re.compile(r"&&"),
    re.compile(r"\|\|"),
]
_COG_STRUCT_RUBY = [
    re.compile(r"(?<!\bels)\bif\b"),
    re.compile(r"\bunless\b"),
    re.compile(r"\bwhile\b"),
    re.compile(r"\buntil\b"),
    re.compile(r"\bfor\b"),
    re.compile(r"\bcase\b"),
    re.compile(r"\brescue\b"),
]
_COG_HYBRID_RUBY = [
    re.compile(r"\belsif\b"),
    re.compile(r"\belse\b(?!\s+if)"),
]

# ── R extras ───────────────────────────────────────────────────────────────
_CC_R = [
    re.compile(r"\bif\s*\("),
    re.compile(r"\belse\s+if\s*\("),
    re.compile(r"\bwhile\s*\("),
    re.compile(r"\bfor\s*\("),
    re.compile(r"\bswitch\s*\("),
    re.compile(r"\btryCatch\s*\("),
    re.compile(r"&&"),
    re.compile(r"\|\|"),
]
_COG_STRUCT_R = [
    re.compile(r"(?<!\belse\s)\bif\s*\("),
    re.compile(r"\bwhile\s*\("),
    re.compile(r"\bfor\s*\("),
    re.compile(r"\bswitch\s*\("),
    re.compile(r"\btryCatch\s*\("),
]
_COG_HYBRID_R = [
    re.compile(r"\belse\s+if\s*\("),
    re.compile(r"\belse\b(?!\s+if)"),
]


def _patterns_for(lang: str):
    """Return (cc_patterns, cog_struct_patterns, cog_hybrid_patterns) for a language."""
    _PATTERN_MAP = {
        "js": (_CC_COMMON + _CC_JS_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_JS_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_JS_EXTRA),
        "cs": (_CC_COMMON + _CC_CS_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_CS_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_CS_EXTRA),
        "java": (_CC_COMMON + _CC_JAVA_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_JAVA_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_JAVA_EXTRA),
        "c": (_CC_COMMON + _CC_C_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_C_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_C_EXTRA),
        "cpp": (_CC_COMMON + _CC_C_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_C_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_C_EXTRA),
        "go": (_CC_COMMON + _CC_GO_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_GO_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_GO_EXTRA),
        "rust": (_CC_COMMON + _CC_RUST_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_RUST_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_RUST_EXTRA),
        "kotlin": (_CC_COMMON + _CC_KOTLIN_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_KOTLIN_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_KOTLIN_EXTRA),
        "php": (_CC_COMMON + _CC_PHP_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_PHP_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_PHP_EXTRA),
        "swift": (_CC_COMMON + _CC_SWIFT_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_SWIFT_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_SWIFT_EXTRA),
        "dart": (_CC_COMMON + _CC_DART_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_DART_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_DART_EXTRA),
        "scala": (_CC_COMMON + _CC_SCALA_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_SCALA_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_SCALA_EXTRA),
        # Non-brace languages get their own full pattern sets
        "py": (_CC_PYTHON, _COG_STRUCT_PYTHON, _COG_HYBRID_PYTHON),
        "ruby": (_CC_RUBY, _COG_STRUCT_RUBY, _COG_HYBRID_RUBY),
        "r": (_CC_R, _COG_STRUCT_R, _COG_HYBRID_R),
    }
    return _PATTERN_MAP.get(lang, (_CC_COMMON, _COG_STRUCT_COMMON, _COG_HYBRID_COMMON))


# ─── File analyzers ────────────────────────────────────────────────────────

# Regex helpers for logical operator sequence detection (Fundamental increments)
_RE_LOGICAL_AND = re.compile(r"&&")
_RE_LOGICAL_OR = re.compile(r"\|\|")
_RE_PY_KW_AND = re.compile(r"\band\b")
_RE_PY_KW_OR = re.compile(r"\bor\b")


def _count_operator_sequence_changes(ops: list) -> int:
    """ops: list of (position, kind); +1 per contiguous run of same kind, +1 when kind changes."""
    if not ops:
        return 0
    ops.sort(key=lambda x: x[0])
    sequences = 1
    for i in range(1, len(ops)):
        if ops[i][1] != ops[i - 1][1]:
            sequences += 1
    return sequences


def _count_logical_operator_sequences(stripped: str) -> int:
    """Count cognitive increments for logical operator sequences.

    Per SonarSource Cognitive Complexity spec:
      - Each SEQUENCE of identical operators counts as +1
      - When the operator type changes, a new sequence starts (+1)

    Examples:
      a && b              →  1  (one && sequence)
      a && b && c         →  1  (one && sequence)
      a || b || c         →  1  (one || sequence)
      a && b || c         →  2  (one && seq + one || seq)
      a && b || c && d    →  3  (&&, ||, &&)
      a || b && c || d    →  3  (||, &&, ||)
    """
    ops = []
    for m in _RE_LOGICAL_AND.finditer(stripped):
        ops.append((m.start(), "&&"))
    for m in _RE_LOGICAL_OR.finditer(stripped):
        ops.append((m.start(), "||"))
    return _count_operator_sequence_changes(ops)


def _count_python_keyword_logical_sequences(stripped: str) -> int:
    """Fundamental increments for Python `and` / `or` (same sequence rules as && / ||)."""
    ops = []
    for m in _RE_PY_KW_AND.finditer(stripped):
        ops.append((m.start(), "and"))
    for m in _RE_PY_KW_OR.finditer(stripped):
        ops.append((m.start(), "or"))
    return _count_operator_sequence_changes(ops)


def _count_ruby_logical_sequences(stripped: str) -> int:
    """Ruby: merge &&, ||, and keyword `and` / `or` by source order."""
    ops = []
    for m in _RE_LOGICAL_AND.finditer(stripped):
        ops.append((m.start(), "&&"))
    for m in _RE_LOGICAL_OR.finditer(stripped):
        ops.append((m.start(), "||"))
    for m in _RE_PY_KW_AND.finditer(stripped):
        ops.append((m.start(), "and"))
    for m in _RE_PY_KW_OR.finditer(stripped):
        ops.append((m.start(), "or"))
    return _count_operator_sequence_changes(ops)


_RE_TRY = re.compile(r"\btry\s*\{")
_RE_FINALLY = re.compile(r"\bfinally\s*\{")
_RE_NAMESPACE = re.compile(r"\bnamespace\s+")
_RE_CLASS_LIKE = re.compile(r"\b(?:class|struct|enum|interface|record)\s+")


def _analyze_cstyle(content: str, fm: FileMetrics) -> FileMetrics:
    """Analyze a C-style (brace-delimited) language file.

    Works for: JS/TS, C#, Java, C, C++, Go, Rust, Kotlin, PHP, Swift, Dart, Scala.

    Cognitive Complexity is calculated per the SonarSource 2023 specification:
      - Structural:    +1 + nesting_level  (if, for, while, switch, catch, ternary)
      - Hybrid:        +1 only             (else, else if) — increases nesting
      - Fundamental:   +1 per sequence     (logical operator sequences)
      - Ignored:       try, finally, synchronized, ??, ?.
    """
    cc_pats, cog_struct_pats, cog_hybrid_pats = _patterns_for(fm.lang)
    lines = content.split("\n")
    fm.total_lines = len(lines)

    in_block_comment = False
    nesting_stack = []
    cognitive_nesting = 0

    # Determine function detection pattern for this language
    _FUNC_PATTERNS = {
        "cs": _FUNC_CS, "js": _FUNC_JS, "java": _FUNC_JAVA,
        "c": _FUNC_C, "cpp": _FUNC_C, "go": _FUNC_GO, "rust": _FUNC_RUST,
        "kotlin": _FUNC_KOTLIN, "php": _FUNC_PHP, "swift": _FUNC_SWIFT,
        "dart": _FUNC_DART, "scala": _FUNC_SCALA,
    }
    func_pat = _FUNC_PATTERNS.get(fm.lang)

    for line in lines:
        stripped = line.strip()

        # ── Line classification ──
        if not stripped:
            fm.blank_lines += 1
            continue

        if in_block_comment:
            fm.comment_lines += 1
            if "*/" in stripped:
                in_block_comment = False
            continue

        if stripped.startswith("//"):
            fm.comment_lines += 1
            continue

        if stripped.startswith("/*"):
            fm.comment_lines += 1
            if "*/" not in stripped:
                in_block_comment = True
            continue

        # C# XML doc comments: /// ...
        if fm.lang == "cs" and stripped.startswith("///"):
            fm.comment_lines += 1
            continue

        # Java/Kotlin/Scala Javadoc comments
        if fm.lang in ("java", "kotlin", "scala") and stripped.startswith("/**"):
            fm.comment_lines += 1
            if "*/" not in stripped:
                in_block_comment = True
            continue

        # Rust doc comments: /// or //!
        if fm.lang == "rust" and (stripped.startswith("///") or stripped.startswith("//!")):
            fm.comment_lines += 1
            continue

        # PHP also supports # comments
        if fm.lang == "php" and stripped.startswith("#"):
            fm.comment_lines += 1
            continue

        fm.code_lines += 1

        # ── Function/method detection ──
        if func_pat and func_pat.search(stripped):
            fm.functions += 1

        # ── Cyclomatic complexity ──
        for pattern in cc_pats:
            fm.cyclomatic += len(pattern.findall(stripped))

        # ── Determine if this line has non-nesting braces ──
        is_non_nesting_brace = bool(
            _RE_TRY.search(stripped) or
            _RE_FINALLY.search(stripped) or
            _RE_NAMESPACE.search(stripped) or
            _RE_CLASS_LIKE.search(stripped)
        )

        # ── Process closing braces BEFORE scoring ──
        closes = stripped.count("}")
        for _ in range(closes):
            if nesting_stack:
                was_nesting = nesting_stack.pop()
                if was_nesting:
                    cognitive_nesting = max(0, cognitive_nesting - 1)

        # ── Cognitive complexity (SonarSource 2023 spec) ──
        for pattern in cog_struct_pats:
            matches = pattern.findall(stripped)
            for _ in matches:
                fm.cognitive += 1 + cognitive_nesting

        for pattern in cog_hybrid_pats:
            fm.cognitive += len(pattern.findall(stripped))

        fm.cognitive += _count_logical_operator_sequences(stripped)

        # ── Process opening braces AFTER scoring ──
        opens = stripped.count("{")
        for _ in range(opens):
            if is_non_nesting_brace:
                nesting_stack.append(False)
                is_non_nesting_brace = False
            else:
                nesting_stack.append(True)
                cognitive_nesting += 1

        fm.max_nesting = max(fm.max_nesting, len(nesting_stack))

    return fm


def _analyze_indentation_based(content: str, fm: FileMetrics) -> FileMetrics:
    """Analyze indentation-based languages (Python, Ruby, R).

    Uses indentation level to track nesting depth instead of braces.
    """
    cc_pats, cog_struct_pats, cog_hybrid_pats = _patterns_for(fm.lang)
    lines = content.split("\n")
    fm.total_lines = len(lines)

    in_block_comment = False  # for Ruby =begin/=end and Python triple-quotes
    base_indent = None

    # Determine function detection pattern
    _FUNC_PATTERNS = {"py": _FUNC_PYTHON, "ruby": _FUNC_RUBY, "r": _FUNC_R}
    func_pat = _FUNC_PATTERNS.get(fm.lang)

    for line in lines:
        stripped = line.strip()

        if not stripped:
            fm.blank_lines += 1
            continue

        # ── Comment handling ──
        if fm.lang == "py":
            if in_block_comment:
                fm.comment_lines += 1
                if '"""' in stripped or "'''" in stripped:
                    in_block_comment = False
                continue
            if stripped.startswith('#'):
                fm.comment_lines += 1
                continue
            if stripped.startswith('"""') or stripped.startswith("'''"):
                fm.comment_lines += 1
                # Check if it closes on the same line
                rest = stripped[3:]
                if '"""' not in rest and "'''" not in rest:
                    in_block_comment = True
                continue
        elif fm.lang == "ruby":
            if in_block_comment:
                fm.comment_lines += 1
                if stripped.startswith("=end"):
                    in_block_comment = False
                continue
            if stripped.startswith('#'):
                fm.comment_lines += 1
                continue
            if stripped.startswith("=begin"):
                fm.comment_lines += 1
                in_block_comment = True
                continue
        elif fm.lang == "r":
            if stripped.startswith('#'):
                fm.comment_lines += 1
                continue

        fm.code_lines += 1

        # ── Calculate indentation-based nesting ──
        indent = len(line) - len(line.lstrip())
        if base_indent is None and indent > 0:
            base_indent = indent
        nesting_level = (indent // (base_indent or 4)) if base_indent else 0
        fm.max_nesting = max(fm.max_nesting, nesting_level)

        # ── Function detection ──
        if func_pat and func_pat.search(stripped):
            fm.functions += 1

        # ── Cyclomatic complexity ──
        for pattern in cc_pats:
            fm.cyclomatic += len(pattern.findall(stripped))

        # ── Cognitive complexity ──
        for pattern in cog_struct_pats:
            matches = pattern.findall(stripped)
            for _ in matches:
                fm.cognitive += 1 + nesting_level

        for pattern in cog_hybrid_pats:
            fm.cognitive += len(pattern.findall(stripped))

        # Fundamental: logical operator sequences (Python/Ruby keywords vs C-style &&/||)
        if fm.lang == "py":
            fm.cognitive += _count_python_keyword_logical_sequences(stripped)
        elif fm.lang == "ruby":
            fm.cognitive += _count_ruby_logical_sequences(stripped)

    return fm


# HTML tag nesting patterns
_HTML_OPEN_TAG = re.compile(r"<(\w+)[^>]*/?>|<(\w+)[^>]*>")
_HTML_CLOSE_TAG = re.compile(r"</(\w+)>")
_HTML_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

def _analyze_html(content: str, fm: FileMetrics) -> FileMetrics:
    """Analyze an HTML/Razor file for nesting depth and embedded logic."""
    lines = content.split("\n")
    fm.total_lines = len(lines)
    fm.cyclomatic = 0  # HTML itself starts at 0 (no logic paths)

    in_html_comment = False
    in_script = False
    in_style = False
    nesting_level = 0
    # Reuse C-style analysis for embedded <script> blocks
    script_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            fm.blank_lines += 1
            continue

        # HTML comments: <!-- ... -->
        if in_html_comment:
            fm.comment_lines += 1
            if "-->" in stripped:
                in_html_comment = False
            continue

        if "<!--" in stripped:
            if "-->" not in stripped:
                in_html_comment = True
                fm.comment_lines += 1
                continue
            else:
                # Single-line comment; still count as code if there's other content
                pass

        fm.code_lines += 1

        # Track entering/leaving <script> blocks
        if re.search(r"<script[^>]*>", stripped, re.IGNORECASE):
            in_script = True
        if re.search(r"</script>", stripped, re.IGNORECASE):
            in_script = False

        # Collect script lines for CC analysis
        if in_script:
            script_lines.append(stripped)

        # Track entering/leaving <style> blocks (no complexity, just nesting)
        if re.search(r"<style[^>]*>", stripped, re.IGNORECASE):
            in_style = True
        if re.search(r"</style>", stripped, re.IGNORECASE):
            in_style = False

        # HTML nesting depth (tags)
        for m in _HTML_OPEN_TAG.finditer(stripped):
            tag = (m.group(1) or m.group(2) or "").lower()
            # Skip self-closing and void tags
            if tag and tag not in _HTML_VOID_TAGS and not m.group(0).endswith("/>"):
                nesting_level += 1
        for m in _HTML_CLOSE_TAG.finditer(stripped):
            nesting_level = max(0, nesting_level - 1)

        fm.max_nesting = max(fm.max_nesting, nesting_level)

    # Analyze embedded script blocks for cyclomatic/cognitive complexity
    if script_lines:
        script_content = "\n".join(script_lines)
        temp = FileMetrics("__embedded__", "js")
        temp = _analyze_cstyle(script_content, temp)
        fm.cyclomatic += temp.cyclomatic
        fm.cognitive += temp.cognitive

    return fm


# ─── Function boundary detection ──────────────────────────────────────────

# Regex to extract function/method name (word before opening paren)
_FUNC_NAME_RE = re.compile(r'(\w+)\s*[\(<]')
_FUNC_NAME_KEYWORDS = {
    'if', 'else', 'while', 'for', 'foreach', 'switch', 'catch',
    'lock', 'using', 'return', 'new', 'throw', 'typeof', 'sizeof',
    'nameof', 'await', 'when', 'base', 'this', 'checked', 'unchecked',
    'var', 'in', 'from', 'where', 'select', 'orderby', 'join', 'group',
    'into', 'let', 'on', 'equals', 'by', 'ascending', 'descending',
}


def _find_function_boundaries(content: str, lang: str) -> list:
    """Find function/method start and end lines. Returns [(name, start_0idx, end_0idx), ...]."""
    _FUNC_PATS = {
        'cs': _FUNC_CS, 'js': _FUNC_JS, 'java': _FUNC_JAVA,
        'c': _FUNC_C, 'cpp': _FUNC_C, 'go': _FUNC_GO, 'rust': _FUNC_RUST,
        'kotlin': _FUNC_KOTLIN, 'php': _FUNC_PHP, 'swift': _FUNC_SWIFT,
        'dart': _FUNC_DART, 'scala': _FUNC_SCALA,
    }
    func_pat = _FUNC_PATS.get(lang)
    if not func_pat:
        return []

    lines = content.split('\n')
    functions = []
    in_block_comment = False
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        # Skip block comments
        if in_block_comment:
            if '*/' in stripped:
                in_block_comment = False
            i += 1
            continue

        if stripped.startswith('//') or stripped.startswith('///'):
            i += 1
            continue

        if stripped.startswith('/*') or stripped.startswith('/**'):
            if '*/' not in stripped:
                in_block_comment = True
            i += 1
            continue

        # Skip attributes / annotations
        if stripped.startswith('[') and not stripped.startswith('[Key'):
            i += 1
            continue

        # Check for function declaration
        if func_pat.search(stripped):
            # Extract the function name: the word immediately before the
            # first '(' on the line — that's the method/function name.
            paren_idx = stripped.find('(')
            func_name = '?'
            if paren_idx > 0:
                # Walk backwards from '(' to find the identifier
                end = paren_idx - 1
                while end >= 0 and stripped[end] == ' ':
                    end -= 1
                # Handle generic methods: name<T>(  → find name before '<'
                if end >= 0 and stripped[end] == '>':
                    # Skip over generic params: find matching '<'
                    depth_g = 1
                    end -= 1
                    while end >= 0 and depth_g > 0:
                        if stripped[end] == '>': depth_g += 1
                        elif stripped[end] == '<': depth_g -= 1
                        end -= 1
                # Now extract the identifier
                word_end = end + 1
                while end >= 0 and (stripped[end].isalnum() or stripped[end] == '_'):
                    end -= 1
                func_name = stripped[end + 1:word_end]
                if not func_name or func_name in _FUNC_NAME_KEYWORDS:
                    func_name = '?'

            func_start = i

            # Find the opening brace and its matching closing brace
            depth = 0
            found_open = False
            j = i
            matched = False
            while j < len(lines):
                for ch in lines[j]:
                    if ch == '{':
                        depth += 1
                        found_open = True
                    elif ch == '}':
                        depth -= 1
                        if found_open and depth == 0:
                            functions.append((func_name, func_start, j))
                            i = j + 1
                            matched = True
                            break
                if matched:
                    break
                j += 1

            if matched:
                continue

        i += 1

    return functions


def _analyze_functions(content: str, rel_path: str, lang: str) -> list:
    """Find and analyze each function's complexity independently."""
    lines = content.split('\n')
    boundaries = _find_function_boundaries(content, lang)
    result = []

    for name, start, end in boundaries:
        # Extract the function's source code
        func_lines = lines[start:end + 1]
        func_content = '\n'.join(func_lines)

        # Analyze the function body as a standalone unit
        func_fm = FileMetrics('__func__', lang)
        func_fm = _analyze_cstyle(func_content, func_fm)

        fn = FunctionMetrics(name, rel_path, start + 1)  # 1-indexed
        fn.end_line = end + 1
        fn.code_lines = func_fm.code_lines
        fn.cyclomatic = func_fm.cyclomatic
        fn.cognitive = func_fm.cognitive
        # Subtract 1 from nesting: the function's own { } is a structural
        # brace, not a control-flow nesting level.
        fn.max_nesting = max(0, func_fm.max_nesting - 1)

        result.append(fn)

    return result


def analyze_file(filepath: str, rel_path: str) -> FileMetrics:
    """Compute complexity metrics for a single file (any supported language)."""
    ext = os.path.splitext(filepath)[1].lstrip(".").lower()
    lang = _get_lang(ext)

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    fm = FileMetrics(rel_path, lang)

    if lang == "html":
        return _analyze_html(content, fm)
    elif lang in ("py", "ruby", "r"):
        fm = _analyze_indentation_based(content, fm)
        # Python and Ruby can still have function-level analysis via indentation
        return fm
    else:
        fm = _analyze_cstyle(content, fm)
        fm.function_metrics = _analyze_functions(content, rel_path, lang)
        return fm


# ─── Project scanning ──────────────────────────────────────────────────────

# ─── Exclusion helpers ─────────────────────────────────────────────────────

def _should_exclude(rel_path: str, fname: str, excludes: list) -> bool:
    """Check if a file should be excluded based on user-supplied patterns.

    Each pattern is matched against:
      1. The filename         (e.g. 'foo.cs' matches file foo.cs anywhere)
      2. The file extension   (e.g. '.min.js' matches any file ending in .min.js)
      3. The relative path    (e.g. 'old/' matches any file under an 'old' directory)
      4. Glob against relpath (e.g. '*/Controllers/*' or '**/*.test.ts')

    Patterns are case-insensitive.
    """
    rel_lower = rel_path.lower().replace(os.sep, "/")
    fname_lower = fname.lower()

    for pattern in excludes:
        p = pattern.strip().lower().replace(os.sep, "/")
        if not p:
            continue

        # 1. Extension match: pattern starts with '.'
        if p.startswith(".") and fname_lower.endswith(p):
            return True

        # 2. Directory/subpath match: pattern ends with '/'
        if p.endswith("/") and (f"/{p}" in f"/{rel_lower}/" or rel_lower.startswith(p)):
            return True

        # 3. Exact filename match
        if fname_lower == p:
            return True

        # 4. Directory name match (without trailing slash)
        if "/" not in p and not p.startswith(".") and f"/{p}/" in f"/{rel_lower}":
            return True

        # 5. Glob / fnmatch against full relative path
        if fnmatch.fnmatch(rel_lower, p):
            return True

        # 6. Substring match for paths containing '/'
        if "/" in p and p in rel_lower:
            return True

    return False


def scan_project(root_dir: str, excludes: list = None) -> list:
    """Walk the directory tree and analyze all matching files."""
    all_metrics = []
    excludes = excludes or []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for fname in filenames:
            ext = os.path.splitext(fname)[1]
            if ext.lower() not in {e.lower() for e in EXTENSIONS}:
                continue
            if any(fname.endswith(s) for s in SKIP_SUFFIXES):
                continue

            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root_dir)

            if excludes and _should_exclude(rel, fname, excludes):
                continue

            try:
                fm = analyze_file(fpath, rel)
                all_metrics.append(fm)
            except Exception as e:
                print(f"  ⚠ Error reading {rel}: {e}", file=sys.stderr)

    return all_metrics


# ─── Categorization helpers ────────────────────────────────────────────────

def categorize(metrics: list) -> dict:
    """Split files into logical categories for clearer reporting."""
    cats = {
        "ui": [],        # Generic UI wrapper components (shadcn, etc.)
        "business": [],  # Application-specific logic and components
        "config": [],    # Config / setup files
        "test": [],      # Test files
        "types": [],     # Type definition files
        "markup": [],    # HTML / Razor views
    }
    for m in metrics:
        p = m.path.lower()
        if "_test." in p or ".test." in p or "/test/" in p or "/__tests__/" in p or "test.java" in p or "tests.cs" in p:
            cats["test"].append(m)
        elif m.lang == "html":
            cats["markup"].append(m)
        elif p.endswith("types.ts") or p.endswith("types.tsx") or "/types/" in p:
            cats["types"].append(m)
        elif any(p.endswith(s) for s in (
            "config.ts", "config.tsx", "config.js", "config.mjs",
            "config.cs", "startup.cs", "program.cs",
        )) or "setup" in p:
            cats["config"].append(m)
        elif "/components/ui/" in p or "/ui/" in p:
            cats["ui"].append(m)
        else:
            cats["business"].append(m)
    return cats


def health_score(metrics: list) -> float:
    """Calculate a 1.0–5.0 overall health score."""
    if not metrics:
        return 5.0

    cm = _metrics_excluding_markup(metrics)
    n = len(cm)
    total_code = sum(m.code_lines for m in metrics)
    total_comments = sum(m.comment_lines for m in metrics)
    comment_ratio = (total_comments / total_code * 100) if total_code else 0

    score = 5.0

    if n:
        avg_cc = sum(m.cyclomatic for m in cm) / n
        avg_cog = sum(m.cognitive for m in cm) / n
        max_nest = max(m.max_nesting for m in cm)
        very_high = sum(1 for m in cm if m.cyclomatic > CC_HIGH)
        extreme_cc = sum(1 for m in cm if m.cyclomatic > CC_VERY_HIGH)

        # Cyclomatic average penalty
        if avg_cc > 20:
            score -= 1.5
        elif avg_cc > 10:
            score -= 0.75
        elif avg_cc > 5:
            score -= 0.25

        # Cognitive average penalty
        if avg_cog > 30:
            score -= 1.5
        elif avg_cog > 15:
            score -= 0.75
        elif avg_cog > 8:
            score -= 0.25

        # Proportion of very-high files (CC > 50); extra weight if any extreme (CC > 100)
        if very_high > n * 0.1:
            score -= 0.5
        elif very_high > n * 0.05:
            score -= 0.25
        if extreme_cc > 0 and extreme_cc >= max(1, n * 0.02):
            score -= 0.25

        # Nesting penalty (aligns with NEST_HIGH / NEST_VERY_HIGH bands)
        if max_nest > NEST_VERY_HIGH:
            score -= 0.5
        elif max_nest > NEST_HIGH:
            score -= 0.25

    # Comment ratio penalty (whole project, including markup)
    if comment_ratio < 2:
        score -= 0.5
    elif comment_ratio < 5:
        score -= 0.25

    return max(1.0, min(5.0, round(score, 1)))


# ─── Output formatters ─────────────────────────────────────────────────────

def print_summary(metrics: list, top_n: int = 10, verbose: bool = False):
    """Print a human-readable project summary to stdout."""
    if not metrics:
        print("No files found to analyze.")
        return

    n = len(metrics)
    mcode = _metrics_excluding_markup(metrics)
    ncode = len(mcode)
    total_lines = sum(m.total_lines for m in metrics)
    total_code = sum(m.code_lines for m in metrics)
    total_comments = sum(m.comment_lines for m in metrics)
    total_blank = sum(m.blank_lines for m in metrics)
    total_cc = sum(m.cyclomatic for m in mcode)
    total_cog = sum(m.cognitive for m in mcode)
    comment_ratio = (total_comments / total_code * 100) if total_code else 0
    max_nest = max(m.max_nesting for m in mcode) if mcode else 0

    cc_sorted = sorted(m.cyclomatic for m in mcode)
    cog_sorted = sorted(m.cognitive for m in mcode)
    median_cc = cc_sorted[ncode // 2] if ncode else 0
    median_cog = cog_sorted[ncode // 2] if ncode else 0

    cats = categorize(metrics)

    low = sum(1 for m in mcode if m.cyclomatic <= CC_LOW)
    mod = sum(1 for m in mcode if CC_LOW < m.cyclomatic <= CC_MODERATE)
    high = sum(1 for m in mcode if CC_MODERATE < m.cyclomatic <= CC_HIGH)
    vhigh = sum(1 for m in mcode if CC_HIGH < m.cyclomatic <= CC_VERY_HIGH)
    cext = sum(1 for m in mcode if m.cyclomatic > CC_VERY_HIGH)
    cog_low = sum(1 for m in mcode if m.cognitive <= COG_LOW)
    cog_mod = sum(1 for m in mcode if COG_LOW < m.cognitive <= COG_MODERATE)
    cog_high = sum(1 for m in mcode if COG_MODERATE < m.cognitive <= COG_HIGH)
    cog_vhigh = sum(1 for m in mcode if COG_HIGH < m.cognitive <= COG_VERY_HIGH)
    cog_ext = sum(1 for m in mcode if m.cognitive > COG_VERY_HIGH)
    deep = sum(1 for m in mcode if m.max_nesting >= 4)
    nest_sorted = sorted(m.max_nesting for m in mcode)
    median_nest = nest_sorted[ncode // 2] if ncode else 0
    nest_shallow = sum(1 for m in mcode if m.max_nesting <= NEST_LOW)
    nest_mod = sum(1 for m in mcode if NEST_LOW < m.max_nesting <= NEST_MODERATE)
    nest_high = sum(1 for m in mcode if NEST_MODERATE < m.max_nesting <= NEST_HIGH)
    nest_vhigh = sum(1 for m in mcode if NEST_HIGH < m.max_nesting <= NEST_VERY_HIGH)
    nest_ext = sum(1 for m in mcode if m.max_nesting > NEST_VERY_HIGH)
    fn_sorted = sorted(m.functions for m in mcode)
    median_fn = fn_sorted[ncode // 2] if ncode else 0
    fn_low = sum(1 for m in mcode if m.functions <= FN_LOW)
    fn_mod = sum(1 for m in mcode if FN_LOW < m.functions <= FN_MODERATE)
    fn_high = sum(1 for m in mcode if FN_MODERATE < m.functions <= FN_HIGH)
    fn_vhigh = sum(1 for m in mcode if FN_HIGH < m.functions <= FN_VERY_HIGH)
    fn_ext = sum(1 for m in mcode if m.functions > FN_VERY_HIGH)

    score = health_score(metrics)
    stars = "★" * int(round(score)) + "☆" * (5 - int(round(score)))

    sep = "=" * 62
    print(sep)
    print("  CODE COMPLEXITY ANALYSIS")
    print(sep)
    print()

    # Language breakdown
    _LANG_LABELS = {
        "js": "JS/TS", "cs": "C#", "java": "Java", "html": "HTML",
        "c": "C", "cpp": "C++", "go": "Go", "rust": "Rust",
        "kotlin": "Kotlin", "php": "PHP", "swift": "Swift", "ruby": "Ruby",
        "r": "R", "dart": "Dart", "scala": "Scala", "py": "Python",
    }
    langs = {}
    for m in metrics:
        label = _LANG_LABELS.get(m.lang, m.lang)
        langs[label] = langs.get(label, 0) + 1

    # File breakdown
    print("FILES")
    print(f"  Total files analyzed:  {n}")
    if len(langs) > 1:
        for lbl, cnt in sorted(langs.items()):
            print(f"    {lbl + ':':20s} {cnt}")
    print(f"    UI components:       {len(cats['ui'])}")
    print(f"    Business logic:      {len(cats['business'])}")
    print(f"    Config / setup:      {len(cats['config'])}")
    print(f"    Tests:               {len(cats['test'])}")
    print(f"    Type definitions:    {len(cats['types'])}")
    print(f"    Markup (HTML):       {len(cats['markup'])}")
    print()

    # Size (function counts exclude markup; see FUNCTIONS section)
    total_funcs = sum(m.functions for m in mcode)

    print("SIZE")
    print(f"  Total lines:           {total_lines:,}")
    print(f"  Code lines:            {total_code:,}")
    print(f"  Comment lines:         {total_comments:,}")
    print(f"  Blank lines:           {total_blank:,}")
    print(f"  Comment ratio:         {comment_ratio:.1f}%")
    print(f"  Avg code lines/file:   {total_code / n:.0f}")
    print(f"  Total functions:       {total_funcs:,}  (excl. HTML/markup)")
    avg_fn = total_funcs / ncode if ncode else 0.0
    print(f"  Avg functions/file:    {avg_fn:.1f}  (non-markup files only)")
    print()

    _pct = lambda c: (c / ncode * 100) if ncode else 0.0

    # Cyclomatic
    print("CYCLOMATIC COMPLEXITY  (excl. HTML/markup)")
    print(f"  Total:                 {total_cc:,}")
    print(f"  Average / file:        {total_cc / ncode:.1f}" if ncode else "  Average / file:        —")
    print(f"  Median / file:         {median_cc}")
    print(f"    Low     (1–{CC_LOW}):       {low:>3} files  ({_pct(low):.0f}%)")
    print(f"    Moderate({CC_LOW + 1}–{CC_MODERATE}):    {mod:>3} files  ({_pct(mod):.0f}%)")
    print(f"    High    ({CC_MODERATE + 1}–{CC_HIGH}):   {high:>3} files  ({_pct(high):.0f}%)")
    print(
        f"    V. High ({CC_HIGH + 1}–{CC_VERY_HIGH}): {vhigh:>3} files  "
        f"({_pct(vhigh):.0f}%)"
    )
    print(f"    Extreme (>{CC_VERY_HIGH}):   {cext:>3} files  ({_pct(cext):.0f}%)")
    print()

    # Cognitive
    print("COGNITIVE COMPLEXITY  (excl. HTML/markup)")
    print(f"  Total:                 {total_cog:,}")
    print(f"  Average / file:        {total_cog / ncode:.1f}" if ncode else "  Average / file:        —")
    print(f"  Median / file:         {median_cog}")
    print(f"    Low     (0–{COG_LOW}):       {cog_low:>3} files  ({_pct(cog_low):.0f}%)")
    print(f"    Moderate({COG_LOW + 1}–{COG_MODERATE}):    {cog_mod:>3} files  ({_pct(cog_mod):.0f}%)")
    print(f"    High    ({COG_MODERATE + 1}–{COG_HIGH}):   {cog_high:>3} files  ({_pct(cog_high):.0f}%)")
    print(
        f"    V. High ({COG_HIGH + 1}–{COG_VERY_HIGH}): {cog_vhigh:>3} files  "
        f"({_pct(cog_vhigh):.0f}%)"
    )
    print(f"    Extreme (>{COG_VERY_HIGH}):   {cog_ext:>3} files  ({_pct(cog_ext):.0f}%)")
    print()

    # Nesting
    print("NESTING (max block/brace depth per file, excl. HTML/markup)")
    print(f"  Max depth (project):   {max_nest}")
    print(f"  Median / file:         {median_nest}")
    print(f"    Low     (0–{NEST_LOW}):       {nest_shallow:>3} files  ({_pct(nest_shallow):.0f}%)")
    print(f"    Moderate({NEST_LOW + 1}–{NEST_MODERATE}):    {nest_mod:>3} files  ({_pct(nest_mod):.0f}%)")
    print(f"    High    ({NEST_MODERATE + 1}–{NEST_HIGH}):   {nest_high:>3} files  ({_pct(nest_high):.0f}%)")
    print(
        f"    V. High ({NEST_HIGH + 1}–{NEST_VERY_HIGH}): {nest_vhigh:>3} files  "
        f"({_pct(nest_vhigh):.0f}%)"
    )
    print(f"    Extreme (>{NEST_VERY_HIGH}):   {nest_ext:>3} files  ({_pct(nest_ext):.0f}%)")
    print(f"  Files with depth ≥ 4:  {deep}  (common style / ESLint max-depth default)")
    print()

    # Functions per file
    print("FUNCTIONS (count per file, excl. HTML/markup)")
    print(f"  Total (project):       {total_funcs:,}")
    print(f"  Average / file:        {avg_fn:.1f}" if ncode else "  Average / file:        —")
    print(f"  Median / file:         {median_fn}")
    print(f"    Low     (0–{FN_LOW}):       {fn_low:>3} files  ({_pct(fn_low):.0f}%)")
    print(f"    Moderate({FN_LOW + 1}–{FN_MODERATE}):    {fn_mod:>3} files  ({_pct(fn_mod):.0f}%)")
    print(f"    High    ({FN_MODERATE + 1}–{FN_HIGH}):   {fn_high:>3} files  ({_pct(fn_high):.0f}%)")
    print(
        f"    V. High ({FN_HIGH + 1}–{FN_VERY_HIGH}): {fn_vhigh:>3} files  "
        f"({_pct(fn_vhigh):.0f}%)"
    )
    print(f"    Extreme (>{FN_VERY_HIGH}):   {fn_ext:>3} files  ({_pct(fn_ext):.0f}%)")
    print()

    # Business logic subset
    biz = cats["business"]
    if biz:
        biz_n = len(biz)
        biz_code = sum(m.code_lines for m in biz)
        biz_cc = sum(m.cyclomatic for m in biz)
        biz_cog = sum(m.cognitive for m in biz)
        print("BUSINESS LOGIC ONLY")
        print(f"  Files:                 {biz_n}")
        print(f"  Code lines:            {biz_code:,}")
        print(f"  Avg CC / file:         {biz_cc / biz_n:.1f}")
        print(f"  Avg Cognitive / file:  {biz_cog / biz_n:.1f}")
        print()

    # Top hotspots (complexity tops omit markup; size uses all files)
    by_cc = sorted(mcode, key=lambda m: m.cyclomatic, reverse=True)
    by_cog = sorted(mcode, key=lambda m: m.cognitive, reverse=True)
    by_nest = sorted(mcode, key=lambda m: m.max_nesting, reverse=True)
    by_funcs = sorted(mcode, key=lambda m: m.functions, reverse=True)
    by_size = sorted(metrics, key=lambda m: m.code_lines, reverse=True)

    def _table(title, items, sort_key):
        print(title)
        for m in items[:top_n]:
            print(f"  CC={m.cyclomatic:>4}  Cog={m.cognitive:>5}  "
                  f"Nest={m.max_nesting:>2}  Fns={m.functions:>3}  Lines={m.code_lines:>5}  {m.path}")
        print()

    _table(f"TOP {top_n} — HIGHEST CYCLOMATIC COMPLEXITY", by_cc, "cyclomatic")
    _table(f"TOP {top_n} — HIGHEST COGNITIVE COMPLEXITY", by_cog, "cognitive")
    _table(f"TOP {top_n} — DEEPEST NESTING", by_nest, "max_nesting")
    _table(f"TOP {top_n} — MOST FUNCTIONS", by_funcs, "functions")
    _table(f"TOP {top_n} — LARGEST FILES", by_size, "code_lines")

    # ── Per-function top lists ── (omit markup)
    all_funcs = []
    for m in mcode:
        all_funcs.extend(m.function_metrics)

    if all_funcs:
        fn_by_cc = sorted(all_funcs, key=lambda f: f.cyclomatic, reverse=True)
        fn_by_cog = sorted(all_funcs, key=lambda f: f.cognitive, reverse=True)
        fn_by_nest = sorted(all_funcs, key=lambda f: f.max_nesting, reverse=True)

        def _fn_table(title, items):
            print(title)
            for f in items[:top_n]:
                print(f"  CC={f.cyclomatic:>4}  Cog={f.cognitive:>5}  "
                      f"Nest={f.max_nesting:>2}  Lines={f.code_lines:>5}  "
                      f"{f.name}  ({f.file_path}:{f.start_line})")
            print()

        _fn_table(f"TOP {top_n} FUNCTIONS — HIGHEST CYCLOMATIC COMPLEXITY", fn_by_cc)
        _fn_table(f"TOP {top_n} FUNCTIONS — HIGHEST COGNITIVE COMPLEXITY", fn_by_cog)
        _fn_table(f"TOP {top_n} FUNCTIONS — DEEPEST NESTING", fn_by_nest)

    # Verbose per-file table
    if verbose:
        by_path = sorted(metrics, key=lambda m: m.path)
        print("ALL FILES")
        print(f"  {'File':<60} {'Lang':>5} {'Lines':>6} {'CC':>5} {'Cog':>5} {'Nest':>5} {'Fns':>4}")
        print(f"  {'-' * 60} {'-' * 5} {'-' * 6} {'-' * 5} {'-' * 5} {'-' * 5} {'-' * 4}")
        for m in by_path:
            lang_lbl = _LANG_LABELS.get(m.lang, m.lang)
            print(f"  {m.path:<60} {lang_lbl:>5} {m.code_lines:>6} {m.cyclomatic:>5} "
                  f"{m.cognitive:>5} {m.max_nesting:>5} {m.functions:>4}")
        print()

    # Health score
    print(sep)
    print(f"  OVERALL HEALTH:  {score}/5.0   {stars}")
    print(sep)
    print()

    if score >= 4.0:
        print("  Good overall health. The codebase has manageable complexity.")
    elif score >= 3.0:
        print("  Moderate complexity. Some areas would benefit from refactoring.")
    elif score >= 2.0:
        print("  Elevated complexity. Consider refactoring the hotspot files.")
    else:
        print("  High complexity. Systematic refactoring is recommended.")

    if vhigh:
        print(
            f"\n  {vhigh} file(s) in cyclomatic band "
            f"{CC_HIGH + 1}–{CC_VERY_HIGH} — prioritize refactoring."
        )
    if cext:
        print(
            f"\n  {cext} file(s) exceed cyclomatic >{CC_VERY_HIGH} — "
            "severe hotspots; break up or split files."
        )
    if cog_vhigh:
        print(
            f"\n  {cog_vhigh} file(s) in cognitive band "
            f"{COG_HIGH + 1}–{COG_VERY_HIGH} (aggregate) — simplify control flow."
        )
    if cog_ext:
        print(
            f"\n  {cog_ext} file(s) exceed cognitive >{COG_VERY_HIGH} (aggregate) — "
            "severe complexity; treat as refactor targets."
        )
    if nest_vhigh:
        print(
            f"\n  {nest_vhigh} file(s) with nesting depth "
            f"{NEST_HIGH + 1}–{NEST_VERY_HIGH} — consider flattening or helpers."
        )
    if nest_ext:
        print(
            f"\n  {nest_ext} file(s) exceed nesting depth >{NEST_VERY_HIGH} — "
            "pathological structure; flatten aggressively."
        )
    if fn_vhigh:
        print(
            f"\n  {fn_vhigh} file(s) have {FN_HIGH + 1}–{FN_VERY_HIGH} functions — "
            "large modules; consider splitting."
        )
    if fn_ext:
        print(
            f"\n  {fn_ext} file(s) exceed {FN_VERY_HIGH} functions — "
            "likely god files; split by responsibility."
        )

    print()


def print_json(metrics: list):
    """Output metrics as JSON for tooling integration."""
    n = len(metrics)
    mcode = _metrics_excluding_markup(metrics)
    ncode = len(mcode)
    total_code = sum(m.code_lines for m in metrics)
    total_comments = sum(m.comment_lines for m in metrics)

    output = {
        "summary": {
            "files": n,
            "files_in_complexity_summaries": ncode,
            "total_lines": sum(m.total_lines for m in metrics),
            "code_lines": total_code,
            "comment_lines": total_comments,
            "blank_lines": sum(m.blank_lines for m in metrics),
            "comment_ratio_pct": round(total_comments / total_code * 100, 1) if total_code else 0,
            "cyclomatic_total": sum(m.cyclomatic for m in mcode),
            "cyclomatic_avg": round(sum(m.cyclomatic for m in mcode) / ncode, 1) if ncode else 0,
            "cognitive_total": sum(m.cognitive for m in mcode),
            "cognitive_avg": round(sum(m.cognitive for m in mcode) / ncode, 1) if ncode else 0,
            "cyclomatic_distribution": {
                "low_1_to_10": sum(1 for m in mcode if m.cyclomatic <= CC_LOW),
                "moderate_11_to_20": sum(
                    1 for m in mcode if CC_LOW < m.cyclomatic <= CC_MODERATE
                ),
                "high_21_to_50": sum(
                    1 for m in mcode if CC_MODERATE < m.cyclomatic <= CC_HIGH
                ),
                "very_high_51_to_100": sum(
                    1 for m in mcode if CC_HIGH < m.cyclomatic <= CC_VERY_HIGH
                ),
                "extreme_above_100": sum(1 for m in mcode if m.cyclomatic > CC_VERY_HIGH),
                "thresholds": {
                    "low_max": CC_LOW,
                    "moderate_max": CC_MODERATE,
                    "high_max": CC_HIGH,
                    "very_high_max": CC_VERY_HIGH,
                },
                "reference": "SEI/C4 risk bands; excludes HTML/cshtml/razor",
            },
            "cognitive_distribution": {
                "low_0_to_15": sum(1 for m in mcode if m.cognitive <= COG_LOW),
                "moderate_16_to_25": sum(
                    1 for m in mcode if COG_LOW < m.cognitive <= COG_MODERATE
                ),
                "high_26_to_50": sum(
                    1 for m in mcode if COG_MODERATE < m.cognitive <= COG_HIGH
                ),
                "very_high_51_to_100": sum(
                    1 for m in mcode if COG_HIGH < m.cognitive <= COG_VERY_HIGH
                ),
                "extreme_above_100": sum(1 for m in mcode if m.cognitive > COG_VERY_HIGH),
                "thresholds": {
                    "low_max": COG_LOW,
                    "moderate_max": COG_MODERATE,
                    "high_max": COG_HIGH,
                    "very_high_max": COG_VERY_HIGH,
                },
                "reference": "Sonar S3776 default 15/method; excludes HTML/cshtml/razor",
            },
            "nesting_median": sorted(m.max_nesting for m in mcode)[ncode // 2] if mcode else 0,
            "nesting_distribution": {
                "low_0_to_2": sum(1 for m in mcode if m.max_nesting <= NEST_LOW),
                "moderate_3_to_4": sum(
                    1 for m in mcode if NEST_LOW < m.max_nesting <= NEST_MODERATE
                ),
                "high_5_to_6": sum(
                    1 for m in mcode if NEST_MODERATE < m.max_nesting <= NEST_HIGH
                ),
                "very_high_7_to_9": sum(
                    1 for m in mcode if NEST_HIGH < m.max_nesting <= NEST_VERY_HIGH
                ),
                "extreme_10_plus": sum(1 for m in mcode if m.max_nesting > NEST_VERY_HIGH),
                "thresholds": {
                    "low_max": NEST_LOW,
                    "moderate_max": NEST_MODERATE,
                    "high_max": NEST_HIGH,
                    "very_high_max": NEST_VERY_HIGH,
                },
                "reference": "ESLint max-depth / Sonar S134-style; excludes HTML/cshtml/razor",
            },
            "max_nesting": max(m.max_nesting for m in mcode) if mcode else 0,
            "total_functions": sum(m.functions for m in mcode),
            "functions_avg_per_file": round(
                sum(m.functions for m in mcode) / ncode, 1
            )
            if ncode
            else 0,
            "functions_median_per_file": sorted(m.functions for m in mcode)[ncode // 2]
            if mcode
            else 0,
            "functions_per_file_distribution": {
                "low_0_to_10": sum(1 for m in mcode if m.functions <= FN_LOW),
                "moderate_11_to_25": sum(
                    1 for m in mcode if FN_LOW < m.functions <= FN_MODERATE
                ),
                "high_26_to_50": sum(
                    1 for m in mcode if FN_MODERATE < m.functions <= FN_HIGH
                ),
                "very_high_51_to_100": sum(
                    1 for m in mcode if FN_HIGH < m.functions <= FN_VERY_HIGH
                ),
                "extreme_above_100": sum(1 for m in mcode if m.functions > FN_VERY_HIGH),
                "thresholds": {
                    "low_max": FN_LOW,
                    "moderate_max": FN_MODERATE,
                    "high_max": FN_HIGH,
                    "very_high_max": FN_VERY_HIGH,
                },
                "reference": "Heuristic file-size bands; excludes HTML/cshtml/razor",
            },
            "health_score": health_score(metrics),
        },
        "files": [m.to_dict() for m in sorted(metrics, key=lambda m: m.cyclomatic, reverse=True)],
    }
    print(json.dumps(output, indent=2))


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analyze code complexity across 15 programming languages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported languages:
  JS/TS (.js, .jsx, .ts, .tsx, .mjs, .cjs)
  C# (.cs), Java (.java), Python (.py)
  C (.c, .h), C++ (.cpp, .cc, .cxx, .hpp, .hxx)
  Go (.go), Rust (.rs), Kotlin (.kt, .kts)
  PHP (.php), Swift (.swift), Ruby (.rb)
  R (.r, .R), Dart (.dart), Scala (.scala, .sc)
  HTML (.html, .htm, .cshtml, .razor)

Exclusion examples:
  --exclude old/ docs/          # skip directories
  --exclude .min.js .d.ts       # skip by extension
  --exclude HeromaImport.cs     # skip specific file
  --exclude '*/test/*'          # glob pattern
  --exclude old/ .d.ts foo.cs   # combine multiple

Examples:
  python3 complexity_analysis.py                 # analyze current directory
  python3 complexity_analysis.py ./src            # analyze only src/
  python3 complexity_analysis.py . --verbose      # full per-file table
  python3 complexity_analysis.py . --top 20       # top 20 hotspots
  python3 complexity_analysis.py . --json         # JSON output for CI/tooling
  python3 complexity_analysis.py . --exclude old/ docs/  # skip dirs
        """,
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to analyze (default: current directory)",
    )
    parser.add_argument(
        "--exclude", "-e",
        nargs="+",
        default=[],
        metavar="PATTERN",
        help="Exclude files/dirs matching pattern(s). "
             "Supports: filenames, extensions (.ext), "
             "directories (dir/), globs (*/test/*)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-file detail table",
    )
    parser.add_argument(
        "--top", "-t",
        type=int,
        default=10,
        help="Number of hotspot files to show (default: 10)",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )

    args = parser.parse_args()
    root = os.path.abspath(args.directory)

    if not os.path.isdir(root):
        print(f"Error: '{args.directory}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    metrics = scan_project(root, excludes=args.exclude)

    if args.json_output:
        print_json(metrics)
    else:
        print()
        print(f"  Scanning: {root}")
        if args.exclude:
            print(f"  Excluding: {', '.join(args.exclude)}")
        print(f"  Extensions: {', '.join(sorted(EXTENSIONS))}")
        print()
        print_summary(metrics, top_n=args.top, verbose=args.verbose)


if __name__ == "__main__":
    main()
