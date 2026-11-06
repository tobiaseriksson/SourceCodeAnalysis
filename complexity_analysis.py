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
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts",
    # Single-file components (only the <script> blocks are analyzed)
    ".vue", ".svelte",
    # C#
    ".cs",
    # Java
    ".java",
    # C / C++
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx",
    # Objective-C (.m is only analyzed if it looks like Objective-C, not MATLAB)
    ".m", ".mm",
    # Groovy / Gradle
    ".groovy", ".gradle",
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
# Extensionless files recognised by exact name
FILENAME_LANGS = {"Jenkinsfile": "groovy"}
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt",
    ".lovable", ".gemini", ".vscode", ".idea", "coverage", "__pycache__",
    "bin", "obj", "target", "out", ".gradle", ".mvn", "packages",
    "vendor", "Pods", ".pub-cache",
}
SKIP_SUFFIXES = {".d.ts", ".min.js", ".bundle.js", ".Designer.cs", ".g.cs", ".g.i.cs"}

# Language families
LANG_JS = {"js", "jsx", "ts", "tsx", "mjs", "cjs", "mts", "cts"}
LANG_VUE = {"vue"}
LANG_SVELTE = {"svelte"}
LANG_OBJC = {"m", "mm"}
LANG_GROOVY = {"groovy", "gradle"}
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
               LANG_SCALA | LANG_PHP | LANG_VUE | LANG_SVELTE | LANG_OBJC |
               LANG_GROOVY)

# Single-file component languages: the <script> blocks are extracted and
# analyzed as JS/TS; <template>/<style> are ignored (same as SonarJS).
SFC_LANGS = {"vue", "svelte"}

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

# C#: method / constructor / destructor / operator declarations. Either modifiers
# (return type optional: constructors) or a return type is required, so plain calls
# like `Foo(x)` do not match. Methods without a modifier (private by default),
# generic methods `Name<T>(`, explicit interface implementations `IFoo.Bar(` and
# tuple return types are covered. Statements that still match (`return Foo(a,`,
# `await Task.WhenAll(`...) are rejected in _match_function_decl.
_CS_MODIFIERS = (r"(?:public|private|protected|internal|static|virtual|override|abstract|"
                 r"async|sealed|partial|new|extern|unsafe|readonly|required|file)")
_CS_TYPE = r"(?:\w[\w<>\[\],.\s?]*|\([^()]*\)\??)"
_FUNC_CS = re.compile(
    r"^\s*(?:(?:" + _CS_MODIFIERS + r"\s+)+(?:" + _CS_TYPE + r"\s+)?|" + _CS_TYPE + r"\s+)"
    r"(?:[\w.]+\.)?\w+\s*(?:<[^()]*>)?\s*\("
    r"|^\s*~\w+\s*\("                                    # destructor
    r"|\boperator\s*(?:[^\s\w(]+|true|false)\s*\("      # operator +( / operator ==(
)
# C# property/indexer/event accessor with a block body:  get {  /  private set  (Allman)
_CS_ACCESSOR = re.compile(
    r"^(?:(?:public|private|protected|internal|readonly)\s+)*(get|set|init|add|remove)\s*(?:\{|$)")
# C# property / indexer / event declaration (no parameter list): its name labels accessors
_CS_PROPERTY = re.compile(
    r"^(?:[\w<>\[\],.?]+\s+)+(\w+|this\s*\[[^\]]*\])\s*(?:\{.*)?$")
# JS/TS: function declarations, arrow functions, class methods
_FUNC_JS = re.compile(
    r"(?:"
    r"\bfunction\s+\w+\s*\(|"                          # function name(
    r"\bfunction\s*\(|"                                 # function(
    r"(?:async\s+)?\w+\s*\([^)]*\)\s*(?::\s*\w[\w<>|&\[\]]*)?\s*\{|"  # method(args) {
    r"(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\([^)]*\)\s*=>"     # const x = (...) =>
    r")",
)
# Java: method declarations (modifiers optional: package-private methods such as
# JUnit 5 `void shouldX() {` have none). Calls/statements are rejected in
# _is_function_decl (trailing ';', control keywords, `return foo(`...).
_FUNC_JAVA = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|abstract|synchronized|native|default)\s+)*"
    r"\w[\w<>\[\],\s\?]*\s+\w+\s*\(",
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
# Objective-C: C functions plus methods such as  - (void)load:(int)x {
_FUNC_OBJC_METHOD = re.compile(r"^\s*[-+]\s*\([^)]*\)\s*(\w+)")
_FUNC_OBJC = re.compile(_FUNC_C.pattern + r"|" + _FUNC_OBJC_METHOD.pattern)
# Groovy: `def name(...) {` or Java-style `Type name(...) {`. Requiring a type/def
# and the brace keeps DSL calls such as `stage('Build') {` from counting.
_FUNC_GROOVY = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|abstract|synchronized)\s+)*"
    r"(?:def|[\w<>\[\],?]+)\s+\w+\s*\([^)]*\)\s*\{",
)

# Function-detection pattern per language key
_FUNC_PATTERNS = {
    "cs": _FUNC_CS, "js": _FUNC_JS, "java": _FUNC_JAVA,
    "c": _FUNC_C, "cpp": _FUNC_C, "go": _FUNC_GO, "rust": _FUNC_RUST,
    "kotlin": _FUNC_KOTLIN, "php": _FUNC_PHP, "swift": _FUNC_SWIFT,
    "dart": _FUNC_DART, "scala": _FUNC_SCALA,
    "vue": _FUNC_JS, "svelte": _FUNC_JS, "objc": _FUNC_OBJC, "groovy": _FUNC_GROOVY,
}

# A line that the function pattern matches is NOT a function declaration when the
# identifier before '(' is a control-flow keyword (`if (x) {`, `} else if (`,
# `for (...) {`, `catch (e) {`, ...).
_CONTROL_KEYWORDS = {
    "if", "else", "elif", "for", "foreach", "while", "do", "switch", "catch",
    "using", "lock", "fixed", "synchronized", "when", "with", "return", "throw",
    "sizeof", "typeof", "nameof", "checked", "unchecked", "await",
}
# Word directly before the name that shows the line is a statement (or a type
# declaration such as a C# 12 primary constructor `class Foo(int x)`), not a function
_NOT_DECL_PREV_WORDS = {
    "new", "return", "throw", "yield", "case", "await", "else", "goto",
    "class", "struct", "record", "interface", "enum",
    # LINQ query clauses
    "where", "select", "from", "in", "let", "join", "on", "equals", "orderby", "group", "by", "into",
}
# Leading attributes / annotations before a declaration:  [HttpGet] ...  /  @Override ...
_RE_LEADING_ATTRS = re.compile(r"^(?:\[[^\]]*\]\s*|@(?!interface\b|implementation\b|end\b)\w+(?:\.\w+)*(?:\([^)]*\))?\s+)+")
# Languages where a matching line ending in ';' is a prototype, abstract/interface
# declaration or a call statement rather than a function definition.
_SEMICOLON_NOT_DECL_LANGS = {"java", "c", "cpp", "objc", "cs", "groovy"}


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
    if ext in LANG_VUE:
        return "vue"
    if ext in LANG_SVELTE:
        return "svelte"
    if ext in LANG_OBJC:
        return "objc"
    if ext in LANG_GROOVY:
        return "groovy"
    return "unknown"


# ── Shared C-style patterns (JS/TS, C#, Java) ──────────────────────────────
#
# Cyclomatic Complexity (McCabe, 1976):
#   CC = 1 + number of decision points in the code.
#   Decision points: if, else if, while, for, case, catch, &&, ||, ?:
#   Note: \bif\s*\( already matches the 'if' inside 'else if',
#   so 'else if' must NOT be listed separately (would double-count).
#
#   Ternary: a `?` with whitespace (or line start/end) on both sides. This skips
#   nullable types (`string? x`), TS optional members (`a?: T`), `?.`, `??`, `?:`,
#   Java wildcards (`<?>`) and Rust's `?` operator, and counts multi-line ternaries.
#
#   Language-specific CC notes:
#   - Python: `if` in `x if cond else y` is not a separate decision; ternary is one pattern.
#   - Go / Rust / Swift: `if`, `for`, `while` take no parentheses (`if x > 0 {`).
#   - Rust: each `=>` arm in match counts (like C switch `case`), not the `match` keyword.
#   - C#: `when` (exception filters and case/switch-arm guards) counts, and so does
#     each non-discard arm of a switch expression (`x switch { A => .., _ => .. }`),
#     like a `case` label.
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
#   It does NOT increase for the function's own body, class/namespace/struct,
#   try/finally, using/lock, object initializers or property accessors: a
#   brace's role is taken from the code before it (or from the previous lines,
#   for a brace on its own line).
#

# Ternary `?`: whitespace (or line start/end) on both sides
_RE_TERNARY = re.compile(r"(?:(?<=\s)|^)\?(?=\s|$)")
# catch, with or without a parameter list; not a promise.catch(...) call
_RE_CATCH = re.compile(r"(?<!\.)\bcatch\b")

_CC_COMMON = [
    re.compile(r"\bif\s*\("),          # matches both 'if' and 'else if'
    re.compile(r"\bwhile\s*\("),
    re.compile(r"\bfor\s*\("),
    re.compile(r"(?<!\bgoto\s)\bcase\s+"),   # not C#'s  goto case X;
    _RE_CATCH,
    re.compile(r"&&"),
    re.compile(r"\|\|"),
    _RE_TERNARY,
]

# Cognitive: structural patterns → +1 + nesting_level
# These also increase nesting for their children.
# NOTE: 'if' here must NOT match 'else if' — that's handled as hybrid.
_COG_STRUCT_COMMON = [
    re.compile(r"(?<!\belse\s)\bif\s*\("),   # standalone 'if' only (not 'else if')
    re.compile(r"\bwhile\s*\("),
    re.compile(r"\bfor\s*\("),
    re.compile(r"\bswitch\s*\("),
    _RE_CATCH,                                # catch is structural per spec
    _RE_TERNARY,                              # ternary operator is structural
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
    # `when` as exception filter / guard, not as an identifier (`DateTime when`):
    re.compile(r"\bwhen\s*\("),                          # catch (E e) when (...)  /  case X when (...)
    re.compile(r"^case\b.*?\bwhen\b(?!\s*\()"),           # case int x when x > 0:
    re.compile(r"(?<!\.)\bwhen\b(?!\s*[(:,)=])(?=.*=>)"),   # switch arm:  A when cond =>
    # (switch-expression arms are counted by the analyzer, which knows the context)
]

# Switch expression:  x switch { ... }  (a switch statement is  switch (x) )
_RE_CS_SWITCH_EXPR = re.compile(r"\bswitch\b(?!\s*\()")

_COG_STRUCT_CS_EXTRA = [
    re.compile(r"\bforeach\s*\("),
    _RE_CS_SWITCH_EXPR,
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

# ── Go / Rust / Swift: conditions without parentheses ─────────────────────
# `if x > 0 {`, `for i := range xs {`, `while let Some(x) = it.next() {`
_CC_NOPAREN = [
    re.compile(r"\bif\b"),             # matches both 'if' and 'else if'
    re.compile(r"\bwhile\b"),
    re.compile(r"\bfor\b"),
    re.compile(r"&&"),
    re.compile(r"\|\|"),
]
_COG_STRUCT_NOPAREN = [
    re.compile(r"(?<!\belse\s)\bif\b"),
    re.compile(r"\bwhile\b"),
    re.compile(r"\bfor\b"),
]
_COG_HYBRID_NOPAREN = [
    re.compile(r"\belse\s+if\b"),
    re.compile(r"\belse\b(?!\s+if)"),
]

# ── Go extras ──────────────────────────────────────────────────────────────
_CC_GO_EXTRA = [
    re.compile(r"\bcase\b"),           # switch / select cases
]
_COG_STRUCT_GO_EXTRA = [
    re.compile(r"\bswitch\b"),
    re.compile(r"\bselect\b"),
]
_COG_HYBRID_GO_EXTRA = []

# ── Rust extras ────────────────────────────────────────────────────────────
# Rust: count each match arm (=>) like C switch counts each case; not match keyword
_CC_RUST_EXTRA = [
    re.compile(r"\bloop\b"),
    re.compile(r"=>"),
]
_COG_STRUCT_RUST_EXTRA = [
    re.compile(r"\bloop\b"),
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
# (repeat { } while x  is counted once, by its `while`, like C's do-while)
_CC_SWIFT_EXTRA = [
    re.compile(r"\bguard\b"),
    re.compile(r"\bcase\b"),
    _RE_CATCH,
    _RE_TERNARY,
]
_COG_STRUCT_SWIFT_EXTRA = [
    re.compile(r"\bguard\b"),
    re.compile(r"\bswitch\b"),
    _RE_CATCH,
    _RE_TERNARY,
]
# A guard's `else` is part of the guard, not a separate branch
_COG_HYBRID_SWIFT = [
    re.compile(r"\belse\s+if\b"),
    re.compile(r"^(?!.*\bguard\b).*?\belse\b(?!\s+if)"),
]

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
        "go": (_CC_NOPAREN + _CC_GO_EXTRA, _COG_STRUCT_NOPAREN + _COG_STRUCT_GO_EXTRA, _COG_HYBRID_NOPAREN + _COG_HYBRID_GO_EXTRA),
        "rust": (_CC_NOPAREN + _CC_RUST_EXTRA, _COG_STRUCT_NOPAREN + _COG_STRUCT_RUST_EXTRA, _COG_HYBRID_NOPAREN + _COG_HYBRID_RUST_EXTRA),
        "kotlin": (_CC_COMMON + _CC_KOTLIN_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_KOTLIN_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_KOTLIN_EXTRA),
        "php": (_CC_COMMON + _CC_PHP_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_PHP_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_PHP_EXTRA),
        "swift": (_CC_NOPAREN + _CC_SWIFT_EXTRA, _COG_STRUCT_NOPAREN + _COG_STRUCT_SWIFT_EXTRA, _COG_HYBRID_SWIFT),
        "dart": (_CC_COMMON + _CC_DART_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_DART_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_DART_EXTRA),
        "scala": (_CC_COMMON + _CC_SCALA_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_SCALA_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_SCALA_EXTRA),
        # Vue / Svelte <script> blocks are JS/TS
        "vue": (_CC_COMMON + _CC_JS_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_JS_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_JS_EXTRA),
        "svelte": (_CC_COMMON + _CC_JS_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_JS_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_JS_EXTRA),
        # Objective-C control flow is C's (@catch is matched by the catch pattern)
        "objc": (_CC_COMMON + _CC_C_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_C_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_C_EXTRA),
        # Groovy control flow is Java's
        "groovy": (_CC_COMMON + _CC_JAVA_EXTRA, _COG_STRUCT_COMMON + _COG_STRUCT_JAVA_EXTRA, _COG_HYBRID_COMMON + _COG_HYBRID_JAVA_EXTRA),
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


def _count_logical_operator_sequences(stripped: str, prev_op: str = None) -> int:
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

    prev_op: the last operator of the same expression on the previous line, when
    the expression continues over lines (a sequence continuing onto this line is
    not a new sequence).
    """
    ops = _logical_ops(stripped)
    n = _count_operator_sequence_changes(ops)
    if n and prev_op and ops[0][1] == prev_op:
        n -= 1
    return n


def _logical_ops(stripped: str) -> list:
    """[(position, '&&' | '||'), ...] in source order."""
    ops = [(m.start(), "&&") for m in _RE_LOGICAL_AND.finditer(stripped)]
    ops += [(m.start(), "||") for m in _RE_LOGICAL_OR.finditer(stripped)]
    return sorted(ops)


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


# Brace roles for cognitive nesting (see _brace_kind)
_RE_NESTING_HEADER_EXTRA = re.compile(r"\b(?:do|repeat)\b")    # do { } while / repeat { } while
_RE_CASE_HEADER = re.compile(r"^(?:case|default)\b")          # case X: {  /  case A -> {
_RE_FUNC_KEYWORD_HEADER = re.compile(r"\b(?:function|delegate|func)\b")
# Lambda arrows per language (C/C++/PHP `->` is member access; Rust/PHP/Scala `=>`
# are match arms / array keys)
_LAMBDA_ARROW = {"cs": "=>", "js": "=>", "vue": "=>", "svelte": "=>", "dart": "=>", "java": "->"}
_RE_TOKENS = re.compile(r"=>|->|[{}();,]")
# A control header whose body is the next line, without braces:  if (x) / else / for (...)
_RE_BRACELESS_HEADER = re.compile(r"^(?:else\s+)?(?:if|for|foreach|while|else|do)\b")
_LINE_CONTINUES_END = ("(", ",", "&&", "||", "+", "*", "/", ".", "=", "=>", "?", ":", "[")
_LINE_CONTINUES_START = (".", "&&", "||", "?", ":", "+", "*", "/")


# Languages with """ multi-line strings: Java text blocks, Kotlin/Scala/Groovy/Dart/
# Swift multi-line strings, C# 11 raw string literals (3+ quotes).
_TRIPLE_DQ_LANGS = {"java", "kotlin", "scala", "groovy", "dart", "swift", "cs"}
_TRIPLE_SQ_LANGS = {"groovy", "dart"}
# ...of which these process backslash escapes inside the triple-quoted string
_TRIPLE_ESCAPE_LANGS = {"java", "groovy", "dart", "swift"}
# Backtick strings: JS template literals (escapes apply), Go raw strings (no escapes)
_BACKTICK_ESCAPE_LANGS = {"js", "vue", "svelte"}
_BACKTICK_RAW_LANGS = {"go"}
# Languages where ordinary "..." / '...' strings may span several lines
_MULTILINE_STRING_LANGS = {"php"}


def _clean_cstyle_code(content: str, lang: str) -> str:
    """Strip comments and string literals from a C-style code string.

    Every stripped character becomes a space and every newline is kept, so the
    result has exactly the same lines (and columns) as the input. Callers rely
    on that: they index the cleaned lines with the raw line numbers.

    Interpolation holes are code and are kept: JS `${...}` in template literals
    and C# `{...}` in $"...", $@"..." and single-$ raw (triple-quote) strings.
    """
    out = []
    n = len(content)
    i = 0
    state = "NORMAL"   # NORMAL | LINE_COMMENT | BLOCK_COMMENT | STRING | VERBATIM
    delim = ""         # closing delimiter of the current STRING
    escapes = True     # whether backslash escapes apply in the current STRING
    interp = None      # None | "js" (${...}) | "cs" ({...}) for the current string
    # Open interpolation holes: [depth of ordinary { } inside the hole, string
    # context (state, delim, escapes, interp) to return to when the hole closes]
    holes = []

    def blank(ch):
        return "\n" if ch == "\n" else " "

    while i < n:
        c = content[i]

        if state == "NORMAL":
            two = content[i:i + 2]
            if two == "//":
                state = "LINE_COMMENT"
                out.append("  ")
                i += 2
            elif two == "/*":
                state = "BLOCK_COMMENT"
                out.append("  ")
                i += 2
            elif lang == "php" and c == "#":
                state = "LINE_COMMENT"
                out.append(" ")
                i += 1
            elif lang == "cs" and c in "$@" and re.match(r'\$*@\$*"|\$+"', content[i:i + 8]):
                # C# string prefixes: $"..." (interpolated), @"..." / $@"..." (verbatim),
                # $"""...""" (raw). $$""" raw strings use {{...}} holes: not tracked.
                m = re.match(r'(\$*@?\$*)"', content[i:i + 8])
                prefix = m.group(1)
                dollars = prefix.count("$")
                k = len(prefix)
                out.append(" " * k)
                i += k
                interp = "cs" if dollars == 1 else None
                if "@" in prefix:
                    state = "VERBATIM"
                    out.append(" ")
                    i += 1
                else:
                    q = 1
                    while i + q < n and content[i + q] == '"':
                        q += 1
                    q = q if q >= 3 else 1
                    state = "STRING"
                    delim = '"' * q
                    escapes = q == 1
                    out.append(" " * q)
                    i += q
            elif c in ('"', "'"):
                triple_ok = ((c == '"' and lang in _TRIPLE_DQ_LANGS) or
                             (c == "'" and lang in _TRIPLE_SQ_LANGS))
                if triple_ok and content.startswith(c * 3, i):
                    k = 3
                    if lang == "cs":  # raw string literals may use 4+ quotes
                        while i + k < n and content[i + k] == '"':
                            k += 1
                    delim = c * k
                    escapes = lang in _TRIPLE_ESCAPE_LANGS
                else:
                    k = 1
                    delim = c
                    escapes = True
                interp = None
                state = "STRING"
                out.append(" " * k)
                i += k
            elif c == "`" and lang in (_BACKTICK_ESCAPE_LANGS | _BACKTICK_RAW_LANGS):
                state = "STRING"
                delim = "`"
                escapes = lang in _BACKTICK_ESCAPE_LANGS
                interp = "js" if escapes else None
                out.append(" ")
                i += 1
            elif holes and c == "}" and holes[-1][0] == 0:
                # End of an interpolation hole: back inside its string
                state, delim, escapes, interp = holes.pop()[1]
                out.append(" ")
                i += 1
            else:
                if holes and c == "{":
                    holes[-1][0] += 1
                elif holes and c == "}":
                    holes[-1][0] -= 1
                out.append(c)
                i += 1

        elif state == "LINE_COMMENT":
            if c == "\n":
                state = "NORMAL"
            out.append(blank(c))
            i += 1

        elif state == "BLOCK_COMMENT":
            if content.startswith("*/", i):
                state = "NORMAL"
                out.append("  ")
                i += 2
            else:
                out.append(blank(c))
                i += 1

        elif interp == "cs" and content.startswith(("{{", "}}"), i):
            out.append("  ")      # escaped brace inside a C# interpolated string
            i += 2

        elif interp == "cs" and c == "{":
            holes.append([0, (state, delim, escapes, interp)])
            state = "NORMAL"
            out.append(" ")
            i += 1

        elif state == "VERBATIM":
            if content.startswith('""', i):
                out.append("  ")
                i += 2
            elif c == '"':
                state = "NORMAL"
                out.append(" ")
                i += 1
            else:
                out.append(blank(c))
                i += 1

        else:  # STRING
            if escapes and c == "\\":
                # Escape sequence. The escaped char may be a newline (line
                # continuation, e.g. in Java text blocks) and must be kept.
                out.append(" ")
                if i + 1 < n:
                    out.append(blank(content[i + 1]))
                i += 2
            elif interp == "js" and content.startswith("${", i):
                holes.append([0, (state, delim, escapes, interp)])
                state = "NORMAL"
                out.append("  ")
                i += 2
            elif content.startswith(delim, i):
                state = "NORMAL"
                out.append(" " * len(delim))
                i += len(delim)
            elif c == "\n" and len(delim) == 1 and delim != "`" and lang not in _MULTILINE_STRING_LANGS:
                # An ordinary string cannot span lines; treat the quote as stray
                # (e.g. a Rust lifetime  'a) so it cannot swallow later lines.
                state = "NORMAL"
                out.append("\n")
                i += 1
            else:
                out.append(blank(c))
                i += 1

    return "".join(out)


# JS/TS function assigned to a name:  export const total = (a, b) => ...
_RE_JS_ASSIGNED_FUNC = re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::[^=]*)?=\s*(?:async\s+)?(?:function\b|\()")
_RE_OPERATOR_NAME = re.compile(r"\boperator\s*([^\s(]+(?:\s+[^\s(]+)?)\s*\(")


def _extract_func_name(stripped: str, lang: str = "") -> tuple:
    """Return (name, previous_word) for a function-declaration line.

    The name is the identifier immediately before the first '(' (generic
    parameters such as name<T>( are skipped). The previous word is the word
    before the (possibly qualified) name, e.g. 'return' in  return Task.WhenAll(.
    '?' when no name is found.
    """
    if lang == "objc":
        m = _FUNC_OBJC_METHOD.match(stripped)
        if m:
            return m.group(1), ""
    if lang == "cs":
        m = _RE_OPERATOR_NAME.search(stripped)
        if m:
            return "operator" + m.group(1).replace(" ", ""), ""
    if lang in ("js", "vue", "svelte"):
        m = _RE_JS_ASSIGNED_FUNC.match(stripped)
        if m:
            return m.group(1), ""
    paren_idx = stripped.find("(")
    if paren_idx <= 0:
        return "?", ""
    end = paren_idx - 1
    while end >= 0 and stripped[end] == " ":
        end -= 1
    # Handle generic methods: name<T>(  → find name before '<'
    if end >= 0 and stripped[end] == ">":
        depth_g = 1
        end -= 1
        while end >= 0 and depth_g > 0:
            if stripped[end] == ">":
                depth_g += 1
            elif stripped[end] == "<":
                depth_g -= 1
            end -= 1
        while end >= 0 and stripped[end] == " ":
            end -= 1
    word_end = end + 1
    while end >= 0 and (stripped[end].isalnum() or stripped[end] == "_"):
        end -= 1
    name = stripped[end + 1:word_end] or "?"
    # Skip a qualifier (Task.WhenAll, IDisposable.Dispose, this.Foo)
    while end >= 0 and (stripped[end].isalnum() or stripped[end] in "_."):
        end -= 1
    # Previous word (e.g. 'new' in  new Foo() {)
    while end >= 0 and stripped[end] == " ":
        end -= 1
    prev_end = end + 1
    while end >= 0 and (stripped[end].isalnum() or stripped[end] == "_"):
        end -= 1
    return name, stripped[end + 1:prev_end]


def _match_function_decl(clean_stripped: str, lang: str):
    """If a cleaned, stripped line declares a function/method, return the text
    from where the declaration starts (so `a(); } catch (e) {` is judged by
    `catch (e) {`, not by `a(`); otherwise None."""
    func_pat = _FUNC_PATTERNS.get(lang)
    if not func_pat:
        return None
    line = _RE_LEADING_ATTRS.sub("", clean_stripped) if lang != "objc" else clean_stripped
    m = func_pat.search(line)
    if not m:
        return None
    if lang in _SEMICOLON_NOT_DECL_LANGS and line.endswith(";"):
        return None
    decl = line[m.start():]
    if lang == "cs":
        # Expression-bodied member (`Foo() => expr`): no block body
        arrow, brace = decl.find("=>"), decl.find("{")
        if arrow >= 0 and (brace < 0 or arrow < brace):
            return None
    name, prev = _extract_func_name(decl, lang)
    if not prev:  # declaration starts mid-line: previous word is before the match
        before = line[:m.start()].split()
        prev = before[-1] if before else ""
    if name in _CONTROL_KEYWORDS:
        return None
    # Statements such as  return foo(a,  /  new Foo() {  /  throw bar(
    if prev in _NOT_DECL_PREV_WORDS and name != "function":
        return None
    return decl


def _is_function_decl(clean_stripped: str, lang: str) -> bool:
    """True if a cleaned, stripped line declares a function/method."""
    return _match_function_decl(clean_stripped, lang) is not None


def _match_accessor(clean_stripped: str, lang: str):
    """C# accessor with a block body (get/set/init/add/remove): its keyword, else None."""
    if lang != "cs":
        return None
    m = _CS_ACCESSOR.match(_RE_LEADING_ATTRS.sub("", clean_stripped))
    return m.group(1) if m else None


def _brace_kind(header: str, lang: str, cog_struct_pats, cog_hybrid_pats) -> str:
    """Role of a `{` from the code before it: 'ctrl' (if/else/loop/switch/catch...),
    'switchexpr' (C# switch expression), 'func' (function, lambda, accessor body)
    or 'other' (class, namespace, try, using, initializer...)."""
    h = header.strip()
    if lang == "cs" and _RE_CS_SWITCH_EXPR.search(h):
        return "switchexpr"
    if _RE_CASE_HEADER.match(h):
        return "other"
    probe = h + " {"
    if (_RE_NESTING_HEADER_EXTRA.search(h)
            or any(p.search(probe) for p in cog_struct_pats)
            or any(p.search(probe) for p in cog_hybrid_pats)):
        return "ctrl"
    arrow = _LAMBDA_ARROW.get(lang)
    if (arrow and arrow in h) or _RE_FUNC_KEYWORD_HEADER.search(h):
        return "func"
    if _match_accessor(h, lang) or _is_function_decl(h, lang):
        return "func"
    return "other"


def _analyze_cstyle(content: str, fm: FileMetrics) -> FileMetrics:
    """Analyze a C-style (brace-delimited) language file.

    Works for: JS/TS, C#, Java, C, C++, Go, Rust, Kotlin, PHP, Swift, Dart, Scala,
    Objective-C, Groovy, and the extracted <script> of Vue/Svelte files.

    Cognitive Complexity is calculated per the SonarSource 2023 specification:
      - Structural:    +1 + nesting_level  (if, for, while, switch, catch, ternary)
      - Hybrid:        +1 only             (else, else if) — increases nesting
      - Fundamental:   +1 per sequence     (logical operator sequences)
      - Ignored:       try, finally, synchronized, ??, ?.
    Nesting comes from braces whose role is control flow, and from lambdas /
    local functions inside a function (see _brace_kind).
    """
    cc_pats, cog_struct_pats, cog_hybrid_pats = _patterns_for(fm.lang)
    lang = fm.lang
    arrow = _LAMBDA_ARROW.get(lang)
    lines = content.split("\n")
    fm.total_lines = len(lines)

    # Pre-process the content to strip out strings and comments for complexity and nesting analysis
    cleaned_content = _clean_cstyle_code(content, lang)
    clean_lines = cleaned_content.split("\n")

    in_block_comment = False
    # Open braces: [kind, nests (bool), paren depth at the brace]
    stack = []
    cognitive_nesting = 0     # number of entries in `stack` that nest
    paren_depth = 0
    # Expression lambdas  x => expr  still open: [paren depth, brace depth]
    inline_lambdas = []
    pending = []              # code since the last brace / ';' (header of an Allman '{')
    # Brace-less bodies:  for (...)  /  if (...) foo();  /  else  on its own line
    awaiting = None           # None | "ctrl" | "else": a header ended the previous line
    virtual = []              # brace depth where each brace-less body started (nests +1)
    logic_prev = None         # last && / || of an expression continuing over lines
    ternaries_in_stmt = 0     # ternaries so far in the current (multi-line) expression
    prev_cs = ""

    def in_function():
        return any(e[0] == "func" for e in stack)

    def next_code_line(idx):
        for k in range(idx + 1, len(clean_lines)):
            t = clean_lines[k].strip()
            if t:
                return t
        return ""

    for i, line in enumerate(lines):
        stripped = line.strip()

        # ── Line classification (uses raw source to count comments correctly) ──
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
        if lang == "cs" and stripped.startswith("///"):
            fm.comment_lines += 1
            continue

        # Java/Kotlin/Scala Javadoc comments
        if lang in ("java", "kotlin", "scala") and stripped.startswith("/**"):
            fm.comment_lines += 1
            if "*/" not in stripped:
                in_block_comment = True
            continue

        # Rust doc comments: /// or //!
        if lang == "rust" and (stripped.startswith("///") or stripped.startswith("//!")):
            fm.comment_lines += 1
            continue

        # PHP also supports # comments
        if lang == "php" and stripped.startswith("#"):
            fm.comment_lines += 1
            continue

        fm.code_lines += 1

        # C# preprocessor directives (#if, #region, ...) are not code paths
        if lang == "cs" and stripped.startswith("#"):
            continue

        # ── Complexity & Nesting Analysis (uses cleaned source to ignore strings/comments) ──
        cs = clean_lines[i].strip()
        if not cs:
            continue

        # ── Function/method detection ──
        if _is_function_decl(cs, lang) or _match_accessor(cs, lang):
            fm.functions += 1

        # ── Cyclomatic complexity ──
        for pattern in cc_pats:
            fm.cyclomatic += len(pattern.findall(cs))

        # ── A header without braces on the previous line: is this line its body? ──
        skip_else_if = False
        if awaiting:
            if cs.startswith("{"):
                pass                                   # the header's own block
            elif awaiting == "else" and re.match(r"if\b", cs):
                skip_else_if = True                    # else <newline> if  ==  else if
            else:
                virtual.append(len(stack))
            awaiting = None

        # ── Events in source order: braces, parens, arrows, structural/hybrid keywords ──
        events = [(m.start(), m.group(0)) for m in _RE_TOKENS.finditer(cs)]
        for pattern in cog_struct_pats:
            events += [(m.start(), "S") for m in pattern.finditer(cs)]
        for pattern in cog_hybrid_pats:
            events += [(m.start(), "H") for m in pattern.finditer(cs)]
        events.sort(key=lambda e: e[0])

        is_case_line = bool(_RE_CASE_HEADER.match(cs))
        seg_start = 0          # start of the code segment before the next brace
        depth_at_start = len(stack)
        # A multi-line ternary continues when a line starts or ends with ? / :
        if not (cs.startswith(("?", ":")) or prev_cs.endswith(("?", ":"))):
            ternaries_in_stmt = 0
        # A logical-operator sequence continues when && / || ends or starts a line
        if not (prev_cs.endswith(("&&", "||")) or cs.startswith(("&&", "||"))):
            logic_prev = None
        for pos, ev in events:
            if ev == "S":
                if skip_else_if and pos == 0:
                    skip_else_if = False                # counted by the `else` (+1)
                    continue
                bonus = len(inline_lambdas) + len(virtual)
                if cs[pos] == "?":
                    bonus += ternaries_in_stmt   # nested/chained  a ? x : b ? y : z
                    ternaries_in_stmt += 1
                fm.cognitive += 1 + cognitive_nesting + bonus
            elif ev == "H":
                fm.cognitive += 1
            elif ev == "(":
                paren_depth += 1
            elif ev == ")":
                paren_depth = max(0, paren_depth - 1)
                inline_lambdas = [l for l in inline_lambdas if l[0] <= paren_depth]
            elif ev in (",", ";"):
                inline_lambdas = [l for l in inline_lambdas
                                  if not (l[0] == paren_depth and l[1] == len(stack))]
            elif ev in ("=>", "->"):
                if stack and stack[-1][0] == "switchexpr" and ev == "=>" and paren_depth == stack[-1][2]:
                    # C# switch-expression arm (a discard `_ =>` / `_ when .. =>`
                    # is the default arm; its guard is counted as `when`)
                    arm = cs[:pos] if cs[:pos].strip() else (pending[-1] if pending else "")
                    if not re.search(r"(?:^|[,{])\s*_\s*(?:when\b.*)?$", arm):
                        fm.cyclomatic += 1
                    if not cs[:pos].strip() and re.search(r"(?<!\.)\bwhen\b(?!\s*[(:,)=])", arm):
                        fm.cyclomatic += 1   # guard on the line above:  A when cond <newline> => ...
                elif (ev == arrow and not is_case_line and in_function()
                        and not cs[pos + 2:].lstrip().startswith("{")
                        and (pos + 2 < len(cs))):
                    # Expression lambda inside a function: nests what follows it
                    inline_lambdas.append([paren_depth, len(stack)])
            elif ev == "{":
                header = cs[seg_start:pos].strip()
                if header:
                    kind = _brace_kind(header, lang, cog_struct_pats, cog_hybrid_pats)
                else:
                    # Brace on its own line: the header is the closest preceding
                    # line(s) that classify (multi-line signatures / conditions)
                    kind = "other"
                    for k in range(1, len(pending) + 1):
                        header = " ".join(pending[-k:])
                        kind = _brace_kind(header, lang, cog_struct_pats, cog_hybrid_pats)
                        if kind != "other":
                            break
                if kind == "func" and arrow and arrow in header and inline_lambdas:
                    # `x =>` then `{` (next line), or `x => new Foo {`: one lambda level
                    inline_lambdas.pop()
                nests = kind in ("ctrl", "switchexpr") or (kind == "func" and in_function())
                stack.append([kind, nests, paren_depth])
                if nests:
                    cognitive_nesting += 1
                fm.max_nesting = max(fm.max_nesting, len(stack))
                seg_start = pos + 1
                pending = []
            elif ev == "}":
                if stack:
                    if stack.pop()[1]:
                        cognitive_nesting -= 1
                inline_lambdas = [l for l in inline_lambdas if l[1] <= len(stack)]
                seg_start = pos + 1
                pending = []

        # ── Logical operator sequences (a sequence may continue from the previous line) ──
        ops = _logical_ops(cs)
        if ops:
            fm.cognitive += _count_logical_operator_sequences(cs, logic_prev)
            logic_prev = ops[-1][1]

        # A lambda inside an open call  .Select(x =>  continues until its ')';
        # one ending the line (`x =>`) continues on the next line; any other
        # lambda not closed by ')', ',', ';' or '}' ends with the line.
        if not (arrow and cs.endswith(arrow)):
            inline_lambdas = [l for l in inline_lambdas if l[0] > 0]

        tail = cs[seg_start:].strip()
        if len(stack) == depth_at_start and not cs.startswith("}"):
            tail = cs             # braces opened and closed on this line:  if (o is { A: 1 })
        if cs.endswith(";") or (cs.endswith(":") and not cs.endswith("::")):
            pending = []          # end of statement, or a label such as  case X:
        elif tail:
            pending = (pending + [tail])[-4:]

        # ── Does this line end with a control header whose body is on the next line? ──
        if not cs.endswith((";", "{", "}")) and (cs.endswith(")") or re.search(r"\b(?:else|do)$", cs)):
            for k in range(1, len(pending) + 1):
                header = " ".join(pending[-k:])
                if _RE_BRACELESS_HEADER.match(header) and header.count("(") == header.count(")"):
                    awaiting = "else" if re.search(r"\belse$", cs) else "ctrl"
                    break
        # A brace-less body ends with its line unless the statement continues
        # (or a block opened in it is still open, or another header follows).
        if virtual and not awaiting:
            nxt = next_code_line(i)
            if not (cs.endswith(_LINE_CONTINUES_END) or nxt.startswith(_LINE_CONTINUES_START)):
                virtual = [v for v in virtual if v < len(stack)]
        prev_cs = cs

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
    func_pat = {"py": _FUNC_PYTHON, "ruby": _FUNC_RUBY, "r": _FUNC_R}.get(fm.lang)

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

# Identifiers reported as '?' rather than as a function name
_FUNC_NAME_KEYWORDS = {
    'if', 'else', 'while', 'for', 'foreach', 'switch', 'catch',
    'lock', 'using', 'return', 'new', 'throw', 'typeof', 'sizeof',
    'nameof', 'await', 'when', 'base', 'this', 'checked', 'unchecked',
    'var', 'in', 'from', 'where', 'select', 'orderby', 'join', 'group',
    'into', 'let', 'on', 'equals', 'by', 'ascending', 'descending',
}


_JS_LANGS = {"js", "vue", "svelte"}


def _next_code(lines: list, j: int) -> str:
    for k in range(j + 1, len(lines)):
        t = lines[k].strip()
        if t:
            return t
    return ""


def _find_statement_end(lines: list, i: int, col: int):
    """End line of the expression starting at line i / column col (the body of a
    JS arrow function `(x) => expr`): where brackets balance and the statement
    does not continue on the next line."""
    depth = 0
    for j in range(i, len(lines)):
        text = lines[j][col:] if j == i else lines[j]
        for ch in text:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
                if depth < 0:          # the arrow was an argument:  f(x => x + 1)
                    return j
        t = lines[j].rstrip()
        if depth == 0 and t and (t.endswith(";") or not (
                t.endswith(_LINE_CONTINUES_END) or _next_code(lines, j).startswith(_LINE_CONTINUES_START))):
            return j
    return len(lines) - 1


def _find_block_end(lines: list, i: int, col: int, lang: str):
    """From line i / column col, find the function's `{` and its matching `}`.

    Returns the 0-based end line, or None when the declaration has no block body:
    a ';' (prototype, abstract member) or, in C#, '=>' (expression-bodied member)
    comes before the first '{'. A JS arrow function with an expression body
    (`const f = (x) => x * 2;`) ends where its statement ends.
    """
    depth = 0
    found_open = False
    for j in range(i, len(lines)):
        text = lines[j][col:] if j == i else lines[j]
        k = 0
        while k < len(text):
            ch = text[k]
            if not found_open and lang in _JS_LANGS and text.startswith("=>", k):
                rest = text[k + 2:].strip() or _next_code(lines, j)
                if not rest.startswith("{"):
                    return _find_statement_end(lines, j, (col if j == i else 0) + k + 2)
                k += 2
                continue
            if not found_open and (ch == ";" or (lang == "cs" and text.startswith("=>", k))):
                return None
            if ch == "{":
                depth += 1
                found_open = True
            elif ch == "}":
                depth -= 1
                if found_open and depth == 0:
                    return j
            k += 1
    return None


def _find_function_boundaries(content: str, lang: str) -> list:
    """Find function/method start and end lines. Returns [(name, start_0idx, end_0idx), ...].

    Works on the cleaned source, so braces and keywords inside comments and
    string literals do not affect detection or brace matching. In C#, accessors
    with a block body are reported as  Property.get / Property.set.
    Nested functions (local functions, lambdas) are part of their enclosing one.
    """
    if lang not in _FUNC_PATTERNS:
        return []

    lines = _clean_cstyle_code(content, lang).split('\n')
    functions = []
    last_property = "?"   # C#: name of the property whose accessors follow
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        decl = _match_function_decl(stripped, lang)
        accessor = None if decl is not None else _match_accessor(stripped, lang)
        if decl is None and accessor is None:
            if lang == "cs":
                m = _CS_PROPERTY.match(_RE_LEADING_ATTRS.sub("", stripped))
                if m:
                    last_property = "this[]" if m.group(1).startswith("this") else m.group(1)
            i += 1
            continue

        if decl is not None:
            func_name, _ = _extract_func_name(decl, lang)
            assigned = _RE_JS_ASSIGNED_FUNC.match(stripped) if lang in _JS_LANGS else None
            if assigned:                       # let h = function (a) { ... }
                func_name = assigned.group(1)
            if func_name in _FUNC_NAME_KEYWORDS:
                func_name = '?'
            col = lines[i].find(decl)
        else:
            func_name = f"{last_property}.{accessor}"
            col = lines[i].find(accessor)

        end = _find_block_end(lines, i, max(col, 0), lang)
        if end is None:
            i += 1
            continue
        functions.append((func_name, i, end))
        i = end + 1

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


_SFC_SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.IGNORECASE | re.DOTALL)


def _extract_sfc_script(content: str) -> str:
    """Keep only the <script> block contents of a Vue/Svelte single-file component.

    Everything outside <script> blocks (template, style, custom blocks) is
    reduced to its newlines, so line numbers in the result match the original
    file. Handles several blocks (e.g. <script> + <script setup>); a block with
    src="..." and no inline code contributes nothing.
    """
    parts = []
    pos = 0
    for m in _SFC_SCRIPT_RE.finditer(content):
        parts.append("\n" * content.count("\n", pos, m.start(1)))
        parts.append(m.group(1))
        pos = m.end(1)
    parts.append("\n" * content.count("\n", pos))
    return "".join(parts)


_OBJC_MARKERS = re.compile(r"^\s*(?:#import\b|#include\b|@implementation\b|@interface\b|@end\b)", re.MULTILINE)


def _looks_like_objc(content: str) -> bool:
    """.m is shared by Objective-C and MATLAB; only Objective-C has these markers."""
    return bool(_OBJC_MARKERS.search(content))


def _detect_lang(filepath: str) -> str:
    """Language key for a path: exact filename first (Jenkinsfile), then extension."""
    fname = os.path.basename(filepath)
    if fname in FILENAME_LANGS:
        return FILENAME_LANGS[fname]
    return _get_lang(os.path.splitext(fname)[1].lstrip("."))


def analyze_file(filepath: str, rel_path: str):
    """Compute complexity metrics for a single file (any supported language).

    Returns None for a file that should not be analyzed (a MATLAB .m file).
    """
    lang = _detect_lang(filepath)

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if lang == "objc" and filepath.lower().endswith(".m") and not _looks_like_objc(content):
        return None

    if lang in SFC_LANGS:
        # Only <script> is analyzed; template/style lines end up as blank lines,
        # so code_lines counts script code only and total_lines the whole file.
        content = _extract_sfc_script(content)

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


_EXTENSIONS_LOWER = {e.lower() for e in EXTENSIONS}


def scan_project(root_dir: str, excludes: list = None) -> list:
    """Walk the directory tree and analyze all matching files."""
    all_metrics = []
    excludes = excludes or []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for fname in filenames:
            ext = os.path.splitext(fname)[1]
            if ext.lower() not in _EXTENSIONS_LOWER and fname not in FILENAME_LANGS:
                continue
            if any(fname.endswith(s) for s in SKIP_SUFFIXES):
                continue

            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root_dir)

            if excludes and _should_exclude(rel, fname, excludes):
                continue

            try:
                fm = analyze_file(fpath, rel)
                if fm is not None:
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
            "config.mts", "config.cts",
            "config.cs", "startup.cs", "program.cs",
            ".gradle", "jenkinsfile",
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
        "vue": "Vue", "svelte": "Svelte", "objc": "Objective-C", "groovy": "Groovy",
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
        print(f"  Extensions: {', '.join(sorted(EXTENSIONS))} (+ {', '.join(sorted(FILENAME_LANGS))})")
        print()
        print_summary(metrics, top_n=args.top, verbose=args.verbose)


if __name__ == "__main__":
    main()
