#!/usr/bin/env python3
"""
Logging Usage Analyzer — Multi-language.

Scans source files and counts logging/diagnostic output statements.
Unlike simple "grep for log", this script uses precise patterns that
match actual logging API calls, avoiding false positives from variable
names like 'catalog', 'dialog', 'blogPost', etc.

Supported languages and patterns:
  C# (.cs):
    - Debug.WriteLine(...)          → level: debug
    - Trace.WriteLine(...)          → level: trace
    - Console.WriteLine(...)        → level: info
    - Console.Write(...)            → level: info
    - _logger.LogInformation(...)   → level: info     (ILogger)
    - _logger.LogWarning(...)       → level: warn     (ILogger)
    - _logger.LogError(...)         → level: error    (ILogger)
    - _logger.LogDebug(...)         → level: debug    (ILogger)
    - _logger.LogCritical(...)      → level: error    (ILogger)
    - _logger.LogTrace(...)         → level: trace    (ILogger)
    - Log.Information(...)          → level: info     (Serilog)
    - Log.Warning(...)              → level: warn     (Serilog)
    - Log.Error(...)                → level: error    (Serilog)

  Java (.java):
    - logger.info(...)              → level: info     (SLF4J/Log4j)
    - logger.debug(...)             → level: debug
    - logger.warn(...)              → level: warn
    - logger.error(...)             → level: error
    - logger.trace(...)             → level: trace
    - System.out.println(...)       → level: info
    - System.err.println(...)       → level: error

  JavaScript/TypeScript (.js, .ts, .tsx, .jsx, .mjs, .cjs):
    - console.log(...)              → level: info
    - console.warn(...)             → level: warn
    - console.error(...)            → level: error
    - console.info(...)             → level: info
    - console.debug(...)            → level: debug
    - console.trace(...)            → level: trace
    - $log.log(...)                 → level: info     (AngularJS)
    - $log.info(...)                → level: info
    - $log.warn(...)                → level: warn
    - $log.error(...)               → level: error
    - $log.debug(...)               → level: debug
    - toastr.success(...)           → level: info     (user notification)
    - toastr.error(...)             → level: error    (user notification)
    - toastr.warning(...)           → level: warn     (user notification)
    - toastr.info(...)              → level: info     (user notification)

  Python (.py):
    - logging.info(...)             → level: info
    - logging.debug(...)            → level: debug
    - logging.warning(...)          → level: warn
    - logging.error(...)            → level: error
    - logging.critical(...)         → level: error
    - logger.info(...)              → level: info
    - logger.debug(...)             → level: debug
    - logger.warning(...)           → level: warn
    - logger.error(...)             → level: error
    - print(...)                    → level: info

  C (.c, .h):
    - printf(...)                   → level: info
    - fprintf(stderr, ...)          → level: error
    - perror(...)                   → level: error
    - syslog(...)                   → level: info     (syslog)

  C++ (.cpp, .cc, .cxx, .hpp, .hxx):
    - std::cout                     → level: info
    - std::cerr                     → level: error
    - std::clog                     → level: debug
    - LOG(INFO)                     → level: info     (glog)
    - LOG(WARNING)                  → level: warn     (glog)
    - LOG(ERROR)                    → level: error    (glog)
    - spdlog::info(...)             → level: info     (spdlog)
    - spdlog::warn(...)             → level: warn     (spdlog)
    - spdlog::error(...)            → level: error    (spdlog)

  Go (.go):
    - fmt.Print/Println/Printf     → level: info
    - log.Print/Println/Printf     → level: info
    - log.Fatal/Fatalln/Fatalf      → level: error
    - log.Panic/Panicln/Panicf      → level: error
    - zap/logrus/zerolog patterns   → level: varies

  Rust (.rs):
    - println!/eprintln!            → level: info/error
    - log::info!/warn!/error!/debug!/trace!
    - tracing::info!/warn!/error!

  Kotlin (.kt, .kts):
    - println(...)                  → level: info
    - logger.info/debug/warn/error
    - Log.d/i/w/e (Android)

  PHP (.php):
    - echo/print                    → level: info
    - error_log(...)                → level: error
    - $logger->info/debug/warning/error (PSR-3)

  Swift (.swift):
    - print(...)                    → level: info
    - NSLog(...)                    → level: info
    - os_log(...)                   → level: info
    - Logger().info/debug/warning/error

  Ruby (.rb):
    - puts/p/pp                     → level: info
    - logger.info/debug/warn/error
    - Rails.logger.*

  R (.r, .R):
    - print(...)                    → level: info
    - cat(...)                      → level: info
    - message(...)                  → level: info
    - warning(...)                  → level: warn
    - stop(...)                     → level: error

  Dart (.dart):
    - print(...)                    → level: info
    - debugPrint(...)               → level: debug
    - log(...)                      → level: info
    - logger.info/warning/severe

  Scala (.scala, .sc):
    - println(...)                  → level: info
    - logger.info/debug/warn/error (SLF4J)
    - System.out/err

How to run:
  From the project root, execute one of the following commands:

    # Analyze the current directory (default)
    python3 logging_analysis.py

    # Analyze a specific directory
    python3 logging_analysis.py ./backend

    # Analyze with per-file detail table (verbose)
    python3 logging_analysis.py ./backend --verbose
    python3 logging_analysis.py ./backend -v

    # Show top N hotspot files (default: 10)
    python3 logging_analysis.py ./backend --top 20
    python3 logging_analysis.py ./backend -t 20

    # Output results as JSON (for CI/tooling integration)
    python3 logging_analysis.py ./backend --json
    python3 logging_analysis.py ./backend -j

    # Exclude files, directories, extensions, or glob patterns
    python3 logging_analysis.py ./backend --exclude old/
    python3 logging_analysis.py ./backend --exclude old/ docs/
    python3 logging_analysis.py ./backend -e .min.js .d.ts
    python3 logging_analysis.py ./backend --exclude HeromaImport.cs
    python3 logging_analysis.py ./backend --exclude '*/test/*'
    python3 logging_analysis.py ./backend --exclude '**/*.spec.ts'

    # Combine flags
    python3 logging_analysis.py ./backend --verbose --top 20 --exclude old/ docs/

  CLI arguments:
    directory            Directory to analyze (default: current directory)
    --verbose, -v        Show a per-file detail table
    --top N, -t N        Number of hotspot files to display (default: 10)
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

Prerequisites:
    Python 3.6+ (no external dependencies)
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
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".cs",
    ".java",
    ".py",
    ".c", ".h",
    ".cpp", ".cc", ".cxx", ".hpp", ".hxx",
    ".go",
    ".rs",
    ".kt", ".kts",
    ".php",
    ".swift",
    ".rb",
    ".r",
    ".dart",
    ".scala", ".sc",
}

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt",
    ".lovable", ".gemini", ".vscode", ".idea", "coverage", "__pycache__",
    "bin", "obj", "target", "out", ".gradle", ".mvn", "packages",
    "lib",  # typically third-party
    "vendor",  # PHP/Go third-party
    "Pods",    # iOS CocoaPods
    ".pub-cache",  # Dart
}

SKIP_SUFFIXES = {".d.ts", ".min.js", ".bundle.js", ".Designer.cs", ".g.cs", ".g.i.cs"}

# Language families
LANG_JS = {"js", "jsx", "ts", "tsx", "mjs", "cjs"}
LANG_CSHARP = {"cs"}
LANG_JAVA = {"java"}
LANG_PYTHON = {"py"}
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


def _get_lang(ext: str) -> str:
    ext = ext.lower()
    if ext in LANG_JS:
        return "js"
    if ext in LANG_CSHARP:
        return "cs"
    if ext in LANG_JAVA:
        return "java"
    if ext in LANG_PYTHON:
        return "py"
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
    return "unknown"


# ─── Logging patterns ──────────────────────────────────────────────────────
#
# Each pattern is a tuple of (compiled_regex, level, category).
#
# The key insight: we match on the METHOD CALL syntax, not just the word "log".
# For example:
#   ✅  console.log(          ← matches: it's console.log followed by (
#   ❌  var dialogRef = ...   ← no match: "log" is inside "dialogRef"
#   ❌  catalog.find(         ← no match: "log" is inside "catalog"
#
# The \b word boundary + \. dot + method name + \s*\( pattern is very precise.


# ── C# patterns ────────────────────────────────────────────────────────────

_LOG_CS = [
    # System.Diagnostics.Debug / Trace
    (re.compile(r'\bDebug\.Write(?:Line)?\s*\('), 'debug', 'diagnostics'),
    (re.compile(r'\bTrace\.Write(?:Line)?\s*\('), 'trace', 'diagnostics'),

    # Console output
    (re.compile(r'\bConsole\.Write(?:Line)?\s*\('), 'info', 'console'),

    # ILogger (Microsoft.Extensions.Logging)
    (re.compile(r'\b\w*[Ll]ogger\.LogInformation\s*\('), 'info', 'ILogger'),
    (re.compile(r'\b\w*[Ll]ogger\.LogWarning\s*\('), 'warn', 'ILogger'),
    (re.compile(r'\b\w*[Ll]ogger\.LogError\s*\('), 'error', 'ILogger'),
    (re.compile(r'\b\w*[Ll]ogger\.LogDebug\s*\('), 'debug', 'ILogger'),
    (re.compile(r'\b\w*[Ll]ogger\.LogCritical\s*\('), 'error', 'ILogger'),
    (re.compile(r'\b\w*[Ll]ogger\.LogTrace\s*\('), 'trace', 'ILogger'),

    # Serilog
    (re.compile(r'\bLog\.Information\s*\('), 'info', 'Serilog'),
    (re.compile(r'\bLog\.Warning\s*\('), 'warn', 'Serilog'),
    (re.compile(r'\bLog\.Error\s*\('), 'error', 'Serilog'),
    (re.compile(r'\bLog\.Fatal\s*\('), 'error', 'Serilog'),
    (re.compile(r'\bLog\.Debug\s*\('), 'debug', 'Serilog'),
    (re.compile(r'\bLog\.Verbose\s*\('), 'trace', 'Serilog'),
]

# ── Java patterns ──────────────────────────────────────────────────────────

_LOG_JAVA = [
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.info\s*\('), 'info', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.debug\s*\('), 'debug', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.warn(?:ing)?\s*\('), 'warn', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.error\s*\('), 'error', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.trace\s*\('), 'trace', 'SLF4J'),
    (re.compile(r'\bSystem\.out\.print(?:ln)?\s*\('), 'info', 'console'),
    (re.compile(r'\bSystem\.err\.print(?:ln)?\s*\('), 'error', 'console'),
]

# ── JavaScript / TypeScript patterns ───────────────────────────────────────

_LOG_JS = [
    (re.compile(r'\bconsole\.log\s*\('), 'info', 'console'),
    (re.compile(r'\bconsole\.warn\s*\('), 'warn', 'console'),
    (re.compile(r'\bconsole\.error\s*\('), 'error', 'console'),
    (re.compile(r'\bconsole\.info\s*\('), 'info', 'console'),
    (re.compile(r'\bconsole\.debug\s*\('), 'debug', 'console'),
    (re.compile(r'\bconsole\.trace\s*\('), 'trace', 'console'),

    # AngularJS $log service
    (re.compile(r'\$log\.log\s*\('), 'info', '$log'),
    (re.compile(r'\$log\.info\s*\('), 'info', '$log'),
    (re.compile(r'\$log\.warn\s*\('), 'warn', '$log'),
    (re.compile(r'\$log\.error\s*\('), 'error', '$log'),
    (re.compile(r'\$log\.debug\s*\('), 'debug', '$log'),

    # toastr (user-facing notifications)
    (re.compile(r'\btoastr\.success\s*\('), 'info', 'toastr'),
    (re.compile(r'\btoastr\.error\s*\('), 'error', 'toastr'),
    (re.compile(r'\btoastr\.warning\s*\('), 'warn', 'toastr'),
    (re.compile(r'\btoastr\.info\s*\('), 'info', 'toastr'),

    # Generic logger (Winston, Bunyan, Pino, custom)
    (re.compile(r'\b(?:this\.)?logger\.info\s*\('), 'info', 'logger'),
    (re.compile(r'\b(?:this\.)?logger\.warn\s*\('), 'warn', 'logger'),
    (re.compile(r'\b(?:this\.)?logger\.error\s*\('), 'error', 'logger'),
    (re.compile(r'\b(?:this\.)?logger\.debug\s*\('), 'debug', 'logger'),
]

# ── Python patterns ────────────────────────────────────────────────────────

_LOG_PYTHON = [
    (re.compile(r'\b(?:logging|logger)\.info\s*\('), 'info', 'logging'),
    (re.compile(r'\b(?:logging|logger)\.debug\s*\('), 'debug', 'logging'),
    (re.compile(r'\b(?:logging|logger)\.warning\s*\('), 'warn', 'logging'),
    (re.compile(r'\b(?:logging|logger)\.error\s*\('), 'error', 'logging'),
    (re.compile(r'\b(?:logging|logger)\.critical\s*\('), 'error', 'logging'),
    (re.compile(r'\b(?:logging|logger)\.exception\s*\('), 'error', 'logging'),
    (re.compile(r'^\s*print\s*\('), 'info', 'print'),
]

# ── C patterns ─────────────────────────────────────────────────────────────

_LOG_C = [
    (re.compile(r'\bprintf\s*\('), 'info', 'printf'),
    (re.compile(r'\bfprintf\s*\(\s*stderr'), 'error', 'fprintf'),
    (re.compile(r'\bfprintf\s*\(\s*stdout'), 'info', 'fprintf'),
    (re.compile(r'\bperror\s*\('), 'error', 'perror'),
    (re.compile(r'\bsyslog\s*\('), 'info', 'syslog'),
    (re.compile(r'\bputs\s*\('), 'info', 'puts'),
    (re.compile(r'\bfputs\s*\('), 'info', 'fputs'),
]

# ── C++ patterns ───────────────────────────────────────────────────────────

_LOG_CPP = [
    # C++ I/O streams
    (re.compile(r'\bstd::cout\b'), 'info', 'iostream'),
    (re.compile(r'\bstd::cerr\b'), 'error', 'iostream'),
    (re.compile(r'\bstd::clog\b'), 'debug', 'iostream'),

    # Google glog
    (re.compile(r'\bLOG\s*\(\s*INFO\s*\)'), 'info', 'glog'),
    (re.compile(r'\bLOG\s*\(\s*WARNING\s*\)'), 'warn', 'glog'),
    (re.compile(r'\bLOG\s*\(\s*ERROR\s*\)'), 'error', 'glog'),
    (re.compile(r'\bLOG\s*\(\s*FATAL\s*\)'), 'error', 'glog'),
    (re.compile(r'\bDLOG\s*\('), 'debug', 'glog'),
    (re.compile(r'\bVLOG\s*\('), 'trace', 'glog'),

    # spdlog
    (re.compile(r'\bspdlog::info\s*\('), 'info', 'spdlog'),
    (re.compile(r'\bspdlog::warn\s*\('), 'warn', 'spdlog'),
    (re.compile(r'\bspdlog::error\s*\('), 'error', 'spdlog'),
    (re.compile(r'\bspdlog::debug\s*\('), 'debug', 'spdlog'),
    (re.compile(r'\bspdlog::trace\s*\('), 'trace', 'spdlog'),
    (re.compile(r'\bspdlog::critical\s*\('), 'error', 'spdlog'),

    # C printf family (inherited from C)
    (re.compile(r'\bprintf\s*\('), 'info', 'printf'),
    (re.compile(r'\bfprintf\s*\(\s*stderr'), 'error', 'fprintf'),
    (re.compile(r'\bstd::format\b'), 'info', 'format'),
]

# ── Go patterns ────────────────────────────────────────────────────────────

_LOG_GO = [
    # fmt package
    (re.compile(r'\bfmt\.Print(?:ln|f)?\s*\('), 'info', 'fmt'),

    # log package (stdlib)
    (re.compile(r'\blog\.Print(?:ln|f)?\s*\('), 'info', 'log'),
    (re.compile(r'\blog\.Fatal(?:ln|f)?\s*\('), 'error', 'log'),
    (re.compile(r'\blog\.Panic(?:ln|f)?\s*\('), 'error', 'log'),

    # logrus
    (re.compile(r'\b(?:logrus|log)\.Info(?:f|ln)?\s*\('), 'info', 'logrus'),
    (re.compile(r'\b(?:logrus|log)\.Debug(?:f|ln)?\s*\('), 'debug', 'logrus'),
    (re.compile(r'\b(?:logrus|log)\.Warn(?:f|ln|ing|ingf)?\s*\('), 'warn', 'logrus'),
    (re.compile(r'\b(?:logrus|log)\.Error(?:f|ln)?\s*\('), 'error', 'logrus'),
    (re.compile(r'\b(?:logrus|log)\.Fatal(?:f|ln)?\s*\('), 'error', 'logrus'),
    (re.compile(r'\b(?:logrus|log)\.Trace(?:f|ln)?\s*\('), 'trace', 'logrus'),

    # zap
    (re.compile(r'\b\w*\.Info\s*\(\s*"'), 'info', 'zap'),
    (re.compile(r'\b\w*\.Debug\s*\(\s*"'), 'debug', 'zap'),
    (re.compile(r'\b\w*\.Warn\s*\(\s*"'), 'warn', 'zap'),
    (re.compile(r'\b\w*\.Error\s*\(\s*"'), 'error', 'zap'),

    # zerolog
    (re.compile(r'\.Info\(\)\.Msg\s*\('), 'info', 'zerolog'),
    (re.compile(r'\.Debug\(\)\.Msg\s*\('), 'debug', 'zerolog'),
    (re.compile(r'\.Warn\(\)\.Msg\s*\('), 'warn', 'zerolog'),
    (re.compile(r'\.Error\(\)\.Msg\s*\('), 'error', 'zerolog'),
]

# ── Rust patterns ──────────────────────────────────────────────────────────

_LOG_RUST = [
    # Standard macros
    (re.compile(r'\bprintln!\s*\('), 'info', 'println'),
    (re.compile(r'\beprintln!\s*\('), 'error', 'eprintln'),
    (re.compile(r'\bprint!\s*\('), 'info', 'print'),
    (re.compile(r'\beprint!\s*\('), 'error', 'eprint'),
    (re.compile(r'\bdbg!\s*\('), 'debug', 'dbg'),

    # log crate
    (re.compile(r'\blog::info!\s*\('), 'info', 'log'),
    (re.compile(r'\blog::debug!\s*\('), 'debug', 'log'),
    (re.compile(r'\blog::warn!\s*\('), 'warn', 'log'),
    (re.compile(r'\blog::error!\s*\('), 'error', 'log'),
    (re.compile(r'\blog::trace!\s*\('), 'trace', 'log'),
    (re.compile(r'\binfo!\s*\('), 'info', 'log'),
    (re.compile(r'\bdebug!\s*\('), 'debug', 'log'),
    (re.compile(r'\bwarn!\s*\('), 'warn', 'log'),
    (re.compile(r'\berror!\s*\('), 'error', 'log'),
    (re.compile(r'\btrace!\s*\('), 'trace', 'log'),

    # tracing crate
    (re.compile(r'\btracing::info!\s*\('), 'info', 'tracing'),
    (re.compile(r'\btracing::debug!\s*\('), 'debug', 'tracing'),
    (re.compile(r'\btracing::warn!\s*\('), 'warn', 'tracing'),
    (re.compile(r'\btracing::error!\s*\('), 'error', 'tracing'),
    (re.compile(r'\btracing::trace!\s*\('), 'trace', 'tracing'),
]

# ── Kotlin patterns ────────────────────────────────────────────────────────

_LOG_KOTLIN = [
    (re.compile(r'\bprintln\s*\('), 'info', 'println'),
    (re.compile(r'\bprint\s*\('), 'info', 'print'),

    # SLF4J / util.logging
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.info\s*\('), 'info', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.debug\s*\('), 'debug', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.warn(?:ing)?\s*\('), 'warn', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.error\s*\('), 'error', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.trace\s*\('), 'trace', 'SLF4J'),

    # Android Log
    (re.compile(r'\bLog\.d\s*\('), 'debug', 'AndroidLog'),
    (re.compile(r'\bLog\.i\s*\('), 'info', 'AndroidLog'),
    (re.compile(r'\bLog\.w\s*\('), 'warn', 'AndroidLog'),
    (re.compile(r'\bLog\.e\s*\('), 'error', 'AndroidLog'),
    (re.compile(r'\bLog\.v\s*\('), 'trace', 'AndroidLog'),
    (re.compile(r'\bLog\.wtf\s*\('), 'error', 'AndroidLog'),

    # Timber (Android)
    (re.compile(r'\bTimber\.d\s*\('), 'debug', 'Timber'),
    (re.compile(r'\bTimber\.i\s*\('), 'info', 'Timber'),
    (re.compile(r'\bTimber\.w\s*\('), 'warn', 'Timber'),
    (re.compile(r'\bTimber\.e\s*\('), 'error', 'Timber'),
]

# ── PHP patterns ───────────────────────────────────────────────────────────

_LOG_PHP = [
    (re.compile(r'\berror_log\s*\('), 'error', 'error_log'),
    (re.compile(r'\btrigger_error\s*\('), 'error', 'trigger_error'),
    (re.compile(r'^\s*echo\b'), 'info', 'echo'),
    (re.compile(r'^\s*print\s'), 'info', 'print'),
    (re.compile(r'\bvar_dump\s*\('), 'debug', 'var_dump'),
    (re.compile(r'\bprint_r\s*\('), 'debug', 'print_r'),

    # PSR-3 Logger Interface (Monolog, etc.)
    (re.compile(r'\$\w*[Ll]ogger->info\s*\('), 'info', 'PSR-3'),
    (re.compile(r'\$\w*[Ll]ogger->debug\s*\('), 'debug', 'PSR-3'),
    (re.compile(r'\$\w*[Ll]ogger->warning\s*\('), 'warn', 'PSR-3'),
    (re.compile(r'\$\w*[Ll]ogger->error\s*\('), 'error', 'PSR-3'),
    (re.compile(r'\$\w*[Ll]ogger->critical\s*\('), 'error', 'PSR-3'),
    (re.compile(r'\$\w*[Ll]ogger->notice\s*\('), 'info', 'PSR-3'),
    (re.compile(r'\$\w*[Ll]ogger->alert\s*\('), 'error', 'PSR-3'),
    (re.compile(r'\$\w*[Ll]ogger->emergency\s*\('), 'error', 'PSR-3'),

    # Laravel Log facade
    (re.compile(r'\bLog::info\s*\('), 'info', 'LaravelLog'),
    (re.compile(r'\bLog::debug\s*\('), 'debug', 'LaravelLog'),
    (re.compile(r'\bLog::warning\s*\('), 'warn', 'LaravelLog'),
    (re.compile(r'\bLog::error\s*\('), 'error', 'LaravelLog'),
    (re.compile(r'\bLog::critical\s*\('), 'error', 'LaravelLog'),
]

# ── Swift patterns ─────────────────────────────────────────────────────────

_LOG_SWIFT = [
    (re.compile(r'^\s*print\s*\('), 'info', 'print'),
    (re.compile(r'\bNSLog\s*\('), 'info', 'NSLog'),
    (re.compile(r'\bos_log\s*\('), 'info', 'os_log'),
    (re.compile(r'\bdebugPrint\s*\('), 'debug', 'debugPrint'),
    (re.compile(r'\bdump\s*\('), 'debug', 'dump'),

    # os.Logger (iOS 14+)
    (re.compile(r'\b\w*[Ll]ogger\.info\s*\('), 'info', 'os.Logger'),
    (re.compile(r'\b\w*[Ll]ogger\.debug\s*\('), 'debug', 'os.Logger'),
    (re.compile(r'\b\w*[Ll]ogger\.warning\s*\('), 'warn', 'os.Logger'),
    (re.compile(r'\b\w*[Ll]ogger\.error\s*\('), 'error', 'os.Logger'),
    (re.compile(r'\b\w*[Ll]ogger\.fault\s*\('), 'error', 'os.Logger'),
    (re.compile(r'\b\w*[Ll]ogger\.notice\s*\('), 'info', 'os.Logger'),
    (re.compile(r'\b\w*[Ll]ogger\.trace\s*\('), 'trace', 'os.Logger'),
    (re.compile(r'\b\w*[Ll]ogger\.critical\s*\('), 'error', 'os.Logger'),

    # SwiftyBeaver / CocoaLumberjack
    (re.compile(r'\blog\.info\s*\('), 'info', 'SwiftyBeaver'),
    (re.compile(r'\blog\.debug\s*\('), 'debug', 'SwiftyBeaver'),
    (re.compile(r'\blog\.warning\s*\('), 'warn', 'SwiftyBeaver'),
    (re.compile(r'\blog\.error\s*\('), 'error', 'SwiftyBeaver'),
    (re.compile(r'\blog\.verbose\s*\('), 'trace', 'SwiftyBeaver'),
]

# ── Ruby patterns ──────────────────────────────────────────────────────────

_LOG_RUBY = [
    (re.compile(r'^\s*puts\b'), 'info', 'puts'),
    (re.compile(r'^\s*p\b'), 'info', 'p'),
    (re.compile(r'^\s*pp\b'), 'debug', 'pp'),
    (re.compile(r'\bwarn\b'), 'warn', 'warn'),
    (re.compile(r'\b\$stderr\.puts\b'), 'error', 'stderr'),

    # Ruby Logger
    (re.compile(r'\b\w*logger\.info\b'), 'info', 'Logger'),
    (re.compile(r'\b\w*logger\.debug\b'), 'debug', 'Logger'),
    (re.compile(r'\b\w*logger\.warn\b'), 'warn', 'Logger'),
    (re.compile(r'\b\w*logger\.error\b'), 'error', 'Logger'),
    (re.compile(r'\b\w*logger\.fatal\b'), 'error', 'Logger'),

    # Rails.logger
    (re.compile(r'\bRails\.logger\.info\b'), 'info', 'RailsLogger'),
    (re.compile(r'\bRails\.logger\.debug\b'), 'debug', 'RailsLogger'),
    (re.compile(r'\bRails\.logger\.warn\b'), 'warn', 'RailsLogger'),
    (re.compile(r'\bRails\.logger\.error\b'), 'error', 'RailsLogger'),
]

# ── R patterns ─────────────────────────────────────────────────────────────

_LOG_R = [
    (re.compile(r'\bprint\s*\('), 'info', 'print'),
    (re.compile(r'\bcat\s*\('), 'info', 'cat'),
    (re.compile(r'\bmessage\s*\('), 'info', 'message'),
    (re.compile(r'\bwarning\s*\('), 'warn', 'warning'),
    (re.compile(r'\bstop\s*\('), 'error', 'stop'),
    (re.compile(r'\bwriteLines\s*\('), 'info', 'writeLines'),

    # futile.logger / log4r / logger
    (re.compile(r'\blog_info\s*\('), 'info', 'futile.logger'),
    (re.compile(r'\blog_debug\s*\('), 'debug', 'futile.logger'),
    (re.compile(r'\blog_warn\s*\('), 'warn', 'futile.logger'),
    (re.compile(r'\blog_error\s*\('), 'error', 'futile.logger'),
    (re.compile(r'\blog_trace\s*\('), 'trace', 'futile.logger'),
]

# ── Dart patterns ──────────────────────────────────────────────────────────

_LOG_DART = [
    (re.compile(r'^\s*print\s*\('), 'info', 'print'),
    (re.compile(r'\bdebugPrint\s*\('), 'debug', 'debugPrint'),

    # dart:developer
    (re.compile(r'\blog\s*\(\s*["\']'), 'info', 'dart:developer'),

    # logger package
    (re.compile(r'\b\w*[Ll]ogger\.info\s*\('), 'info', 'logger'),
    (re.compile(r'\b\w*[Ll]ogger\.d\s*\('), 'debug', 'logger'),
    (re.compile(r'\b\w*[Ll]ogger\.w(?:arning)?\s*\('), 'warn', 'logger'),
    (re.compile(r'\b\w*[Ll]ogger\.(?:e|severe)\s*\('), 'error', 'logger'),
    (re.compile(r'\b\w*[Ll]ogger\.fine\s*\('), 'debug', 'logger'),
    (re.compile(r'\b\w*[Ll]ogger\.shout\s*\('), 'error', 'logger'),
]

# ── Scala patterns ─────────────────────────────────────────────────────────

_LOG_SCALA = [
    (re.compile(r'\bprintln\s*\('), 'info', 'println'),
    (re.compile(r'\bSystem\.out\.print(?:ln)?\s*\('), 'info', 'console'),
    (re.compile(r'\bSystem\.err\.print(?:ln)?\s*\('), 'error', 'console'),

    # SLF4J / Scala Logging
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.info\s*\('), 'info', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.debug\s*\('), 'debug', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.warn(?:ing)?\s*\('), 'warn', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.error\s*\('), 'error', 'SLF4J'),
    (re.compile(r'\b\w*[Ll]og(?:ger)?\.trace\s*\('), 'trace', 'SLF4J'),
]


def _patterns_for(lang: str):
    """Return the list of (regex, level, category) for a language."""
    return {
        "cs": _LOG_CS,
        "java": _LOG_JAVA,
        "js": _LOG_JS,
        "py": _LOG_PYTHON,
        "c": _LOG_C,
        "cpp": _LOG_CPP,
        "go": _LOG_GO,
        "rust": _LOG_RUST,
        "kotlin": _LOG_KOTLIN,
        "php": _LOG_PHP,
        "swift": _LOG_SWIFT,
        "ruby": _LOG_RUBY,
        "r": _LOG_R,
        "dart": _LOG_DART,
        "scala": _LOG_SCALA,
    }.get(lang, [])


# ─── Data class ─────────────────────────────────────────────────────────────

class FileLogMetrics:
    def __init__(self, path: str, lang: str):
        self.path = path
        self.lang = lang
        self.code_lines = 0
        self.total_log_lines = 0
        self.active_log_lines = 0      # uncommented
        self.commented_log_lines = 0   # inside comments
        self.by_level = {"info": 0, "warn": 0, "error": 0, "debug": 0, "trace": 0}
        self.by_category = {}          # e.g. {"console": 5, "toastr": 3}
        self.log_line_details = []     # [(line_no, level, category, is_commented, text), ...]

    @property
    def log_density_pct(self):
        return (self.active_log_lines / self.code_lines * 100) if self.code_lines else 0.0

    def to_dict(self):
        return {
            "path": self.path,
            "language": self.lang,
            "code_lines": self.code_lines,
            "active_log_lines": self.active_log_lines,
            "commented_log_lines": self.commented_log_lines,
            "total_log_lines": self.total_log_lines,
            "log_density_pct": round(self.log_density_pct, 1),
            "by_level": dict(self.by_level),
            "by_category": dict(self.by_category),
        }


# ─── Comment style helpers ─────────────────────────────────────────────────

# Languages using C-style comments (// and /* */)
_CSTYLE_COMMENT_LANGS = {"cs", "java", "js", "c", "cpp", "go", "rust", "kotlin",
                          "swift", "dart", "scala", "php"}
# Languages using # comments
_HASH_COMMENT_LANGS = {"py", "ruby", "r"}

_CSTYLE_LINE_COMMENT = re.compile(r'^\s*//')
_CSTYLE_BLOCK_OPEN = re.compile(r'/\*')
_CSTYLE_BLOCK_CLOSE = re.compile(r'\*/')
_HASH_LINE_COMMENT = re.compile(r'^\s*#')


# ─── Analyzer ──────────────────────────────────────────────────────────────

def analyze_file(filepath: str, rel_path: str) -> FileLogMetrics:
    """Analyze a single file for logging statements."""
    ext = os.path.splitext(filepath)[1].lstrip(".").lower()
    lang = _get_lang(ext)
    patterns = _patterns_for(lang)

    fm = FileLogMetrics(rel_path, lang)

    if not patterns:
        return fm

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lines = content.split("\n")
    in_block_comment = False

    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped:
            continue

        # ── Track comment state ──
        is_commented = False

        if lang in _CSTYLE_COMMENT_LANGS:
            if in_block_comment:
                is_commented = True
                if "*/" in stripped:
                    in_block_comment = False
                continue  # fully inside block comment
            if _CSTYLE_LINE_COMMENT.match(stripped):
                is_commented = True
            elif _CSTYLE_BLOCK_OPEN.search(stripped) and not _CSTYLE_BLOCK_CLOSE.search(stripped):
                if stripped.startswith("/*"):
                    is_commented = True
                    in_block_comment = True
                    continue
                else:
                    in_block_comment = True
            elif stripped.startswith("/*") and _CSTYLE_BLOCK_CLOSE.search(stripped):
                is_commented = True
        elif lang in _HASH_COMMENT_LANGS:
            if _HASH_LINE_COMMENT.match(stripped):
                is_commented = True
        elif lang == "php":
            # PHP also supports # comments
            if stripped.startswith("#"):
                is_commented = True

        if not is_commented:
            fm.code_lines += 1

        # ── Match logging patterns ──
        for pattern, level, category in patterns:
            if pattern.search(stripped):
                fm.total_log_lines += 1

                if is_commented:
                    fm.commented_log_lines += 1
                else:
                    fm.active_log_lines += 1
                    fm.by_level[level] = fm.by_level.get(level, 0) + 1
                    fm.by_category[category] = fm.by_category.get(category, 0) + 1

                fm.log_line_details.append((
                    line_no, level, category, is_commented, stripped[:120]
                ))
                break  # one match per line is enough

    return fm


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


# ─── Project scanning ──────────────────────────────────────────────────────

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


# ─── Language label helper ─────────────────────────────────────────────────

_LANG_LABELS = {
    "js": "JS/TS", "cs": "C#", "java": "Java", "py": "Python",
    "c": "C", "cpp": "C++", "go": "Go", "rust": "Rust",
    "kotlin": "Kotlin", "php": "PHP", "swift": "Swift", "ruby": "Ruby",
    "r": "R", "dart": "Dart", "scala": "Scala",
}


def _lang_label(lang: str) -> str:
    return _LANG_LABELS.get(lang, lang)


# ─── Output formatters ─────────────────────────────────────────────────────

def print_summary(metrics: list, top_n: int = 10, verbose: bool = False):
    """Print a human-readable summary."""
    if not metrics:
        print("No files found to analyze.")
        return

    files_with_logs = [m for m in metrics if m.active_log_lines > 0]
    files_with_commented = [m for m in metrics if m.commented_log_lines > 0]

    n = len(metrics)
    n_with_logs = len(files_with_logs)
    total_code = sum(m.code_lines for m in metrics)
    total_active = sum(m.active_log_lines for m in metrics)
    total_commented = sum(m.commented_log_lines for m in metrics)
    total_all = total_active + total_commented

    # Aggregate by level
    agg_level = {"info": 0, "warn": 0, "error": 0, "debug": 0, "trace": 0}
    for m in metrics:
        for lvl, cnt in m.by_level.items():
            agg_level[lvl] = agg_level.get(lvl, 0) + cnt

    # Aggregate by category
    agg_cat = {}
    for m in metrics:
        for cat, cnt in m.by_category.items():
            agg_cat[cat] = agg_cat.get(cat, 0) + cnt

    # Aggregate by language
    lang_stats = {}
    for m in metrics:
        label = _lang_label(m.lang)
        if label not in lang_stats:
            lang_stats[label] = {"files": 0, "code": 0, "active": 0, "commented": 0}
        lang_stats[label]["files"] += 1
        lang_stats[label]["code"] += m.code_lines
        lang_stats[label]["active"] += m.active_log_lines
        lang_stats[label]["commented"] += m.commented_log_lines

    sep = "=" * 62
    print(sep)
    print("  LOGGING USAGE ANALYSIS")
    print(sep)
    print()

    density = (total_active / total_code * 100) if total_code else 0

    print("OVERVIEW")
    print(f"  Files analyzed:        {n}")
    print(f"  Files with logging:    {n_with_logs}  ({n_with_logs / n * 100:.0f}%)")
    print(f"  Code lines:            {total_code:,}")
    print(f"  Active log lines:      {total_active:,}")
    print(f"  Commented log lines:   {total_commented:,}")
    print(f"  Log density:           {density:.2f}%  (1 log line per {int(total_code / total_active) if total_active else 0} code lines)")
    print()

    print("BY LOG LEVEL (active only)")
    for lvl in ["error", "warn", "info", "debug", "trace"]:
        cnt = agg_level.get(lvl, 0)
        pct = (cnt / total_active * 100) if total_active else 0
        bar = "█" * int(pct / 2)
        print(f"  {lvl:<8} {cnt:>5}  ({pct:>5.1f}%)  {bar}")
    print()

    print("BY LOGGING FRAMEWORK / API")
    for cat, cnt in sorted(agg_cat.items(), key=lambda x: -x[1]):
        pct = (cnt / total_active * 100) if total_active else 0
        print(f"  {cat:<20} {cnt:>5}  ({pct:>5.1f}%)")
    print()

    if len(lang_stats) > 1:
        print("BY LANGUAGE")
        print(f"  {'Language':<12} {'Files':>6} {'Code':>8} {'Logs':>6} {'Commented':>10} {'Density':>8}")
        print(f"  {'-' * 12} {'-' * 6} {'-' * 8} {'-' * 6} {'-' * 10} {'-' * 8}")
        for lbl, st in sorted(lang_stats.items()):
            d = (st["active"] / st["code"] * 100) if st["code"] else 0
            print(f"  {lbl:<12} {st['files']:>6} {st['code']:>8,} {st['active']:>6} {st['commented']:>10} {d:>7.2f}%")
        print()

    # ── Top files ──
    by_active = sorted(files_with_logs, key=lambda m: m.active_log_lines, reverse=True)
    by_density = sorted(
        [m for m in files_with_logs if m.code_lines >= 10],
        key=lambda m: m.log_density_pct, reverse=True
    )

    print(f"TOP {min(top_n, len(by_active))} FILES — MOST LOG LINES")
    for m in by_active[:top_n]:
        levels = "  ".join(f"{k}={v}" for k, v in sorted(m.by_level.items()) if v > 0)
        cats = ", ".join(f"{k}={v}" for k, v in sorted(m.by_category.items()) if v > 0)
        print(f"  {m.active_log_lines:>4} logs  ({m.log_density_pct:>5.1f}%)  "
              f"[{levels}]  {m.path}")
        if cats:
            print(f"       via: {cats}")
    print()

    print(f"TOP {min(top_n, len(by_density))} FILES — HIGHEST LOG DENSITY")
    for m in by_density[:top_n]:
        print(f"  {m.log_density_pct:>5.1f}%  ({m.active_log_lines:>3} / {m.code_lines:>5} lines)  {m.path}")
    print()

    # ── Commented-out logs ──
    if files_with_commented:
        by_commented = sorted(files_with_commented, key=lambda m: m.commented_log_lines, reverse=True)
        print(f"FILES WITH COMMENTED-OUT LOG LINES ({total_commented} total)")
        for m in by_commented[:top_n]:
            print(f"  {m.commented_log_lines:>3} commented  {m.path}")
        print()

    # ── Verbose per-file table ──
    if verbose:
        by_path = sorted(metrics, key=lambda m: m.path)
        print("ALL FILES WITH LOGGING")
        print(f"  {'File':<60} {'Lang':>5} {'Code':>6} {'Logs':>5} {'Cmt':>4} {'Dens%':>6}")
        print(f"  {'-' * 60} {'-' * 5} {'-' * 6} {'-' * 5} {'-' * 4} {'-' * 6}")
        for m in by_path:
            if m.total_log_lines > 0:
                lang_lbl = _lang_label(m.lang)
                print(f"  {m.path:<60} {lang_lbl:>5} {m.code_lines:>6} "
                      f"{m.active_log_lines:>5} {m.commented_log_lines:>4} {m.log_density_pct:>6.1f}")
        print()

    print(sep)
    # Assessment
    if density < 0.5:
        assessment = "Very low — minimal diagnostic output"
    elif density < 2.0:
        assessment = "Low — could benefit from more observability"
    elif density < 5.0:
        assessment = "Moderate — reasonable logging coverage"
    elif density < 10.0:
        assessment = "High — good observability"
    else:
        assessment = "Very high — consider if all logs are necessary"
    print(f"  LOG DENSITY: {density:.2f}%  →  {assessment}")
    print(sep)
    print()


def print_json(metrics: list):
    """Output metrics as JSON."""
    files_with_logs = [m for m in metrics if m.total_log_lines > 0]
    total_code = sum(m.code_lines for m in metrics)
    total_active = sum(m.active_log_lines for m in metrics)
    total_commented = sum(m.commented_log_lines for m in metrics)

    agg_level = {"info": 0, "warn": 0, "error": 0, "debug": 0, "trace": 0}
    agg_cat = {}
    for m in metrics:
        for lvl, cnt in m.by_level.items():
            agg_level[lvl] = agg_level.get(lvl, 0) + cnt
        for cat, cnt in m.by_category.items():
            agg_cat[cat] = agg_cat.get(cat, 0) + cnt

    output = {
        "summary": {
            "files_analyzed": len(metrics),
            "files_with_logging": len(files_with_logs),
            "code_lines": total_code,
            "active_log_lines": total_active,
            "commented_log_lines": total_commented,
            "log_density_pct": round(total_active / total_code * 100, 2) if total_code else 0,
            "by_level": agg_level,
            "by_category": agg_cat,
        },
        "files": [m.to_dict() for m in sorted(
            files_with_logs, key=lambda m: m.active_log_lines, reverse=True
        )],
    }
    print(json.dumps(output, indent=2))


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analyze logging usage across 15 programming languages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported languages:
  JS/TS (.js, .jsx, .ts, .tsx, .mjs, .cjs)
  C# (.cs), Java (.java), Python (.py)
  C (.c, .h), C++ (.cpp, .cc, .cxx, .hpp, .hxx)
  Go (.go), Rust (.rs), Kotlin (.kt, .kts)
  PHP (.php), Swift (.swift), Ruby (.rb)
  R (.r, .R), Dart (.dart), Scala (.scala, .sc)

Exclusion examples:
  --exclude old/ docs/          # skip directories
  --exclude .min.js .d.ts       # skip by extension
  --exclude HeromaImport.cs     # skip specific file
  --exclude '*/test/*'          # glob pattern
  --exclude old/ .d.ts foo.cs   # combine multiple

Examples:
  python3 logging_analysis.py                     # analyze current directory
  python3 logging_analysis.py ./backend            # analyze only backend/
  python3 logging_analysis.py ./frontend --verbose  # full per-file table
  python3 logging_analysis.py . --json             # JSON output for tooling
  python3 logging_analysis.py . --top 20           # top 20 hotspots
  python3 logging_analysis.py . --exclude old/ docs/  # skip directories
        """,
    )
    parser.add_argument("directory", nargs="?", default=".",
                        help="Directory to analyze (default: current directory)")
    parser.add_argument("--exclude", "-e", nargs="+", default=[],
                        metavar="PATTERN",
                        help="Exclude files/dirs matching pattern(s). "
                             "Supports: filenames, extensions (.ext), "
                             "directories (dir/), globs (*/test/*)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-file detail table")
    parser.add_argument("--top", "-t", type=int, default=10,
                        help="Number of hotspot files to show (default: 10)")
    parser.add_argument("--json", "-j", action="store_true", dest="json_output",
                        help="Output results as JSON")

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
        print()
        print_summary(metrics, top_n=args.top, verbose=args.verbose)


if __name__ == "__main__":
    main()
