#!/usr/bin/env python3
"""Analyze git commit history (live `git log` or a pre-exported log file).

Usage:
    python3 analyze_commits.py [PATH]

    PATH — root directory of the Git repository to analyze (default: current directory).
           Ignored when --commit-history is used (except for resolving relative paths).

    python3 analyze_commits.py /path/to/repo
    python3 analyze_commits.py --commit-history commit-export.txt
    python3 analyze_commits.py ./myrepo --exclude vendor/ node_modules/

    python3 analyze_commits.py --export-commit-history
    python3 analyze_commits.py /path/to/repo -E my-export.txt

If --commit-history is omitted, history is fetched with `git log --numstat` in PATH.
Use --export-commit-history (-E) to save that log to commit-history.txt (or a given file).

By default, a "code age" table is printed: bucket granularity depends on repository age
(< 6 months: ISO week; < 2 years: month; else years up to 24+), then top modules per bucket
(--code-age-top-modules, default 5). Use --no-code-age to skip.
"""

import os
import re
import json
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone


import subprocess
import sys


def parse_commit_history(
    exclude_paths=None,
    repo_path=".",
    commit_history_file=None,
    export_commit_history_to=None,
):
    """Load `git log --numstat` output from a file or by running git in ``repo_path``.

    When history is fetched from git and ``export_commit_history_to`` is set, the
    same log text is written to that path before parsing.
    """

    if commit_history_file:
        path = os.path.abspath(commit_history_file)
        print(f"Reading commit history from {path} ...")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as e:
            print(f"Error reading commit history file: {e}")
            sys.exit(1)
    else:
        root = os.path.abspath(repo_path)
        if not os.path.isdir(os.path.join(root, ".git")) and not os.path.isfile(
            os.path.join(root, ".git")
        ):
            print(
                f"Warning: {root!r} does not look like a Git working tree "
                "(no .git). Continuing anyway.\n"
            )
        print(f"Fetching git history in {root} (this takes a few seconds)...")
        try:
            content = subprocess.run(
                ["git", "log", "--numstat", "--no-merges"],
                cwd=root,
                stdout=subprocess.PIPE,
                text=True,
                check=True,
            ).stdout
        except subprocess.CalledProcessError as e:
            print(f"Error calling git: {e}")
            sys.exit(1)

        if export_commit_history_to:
            out_path = os.path.abspath(export_commit_history_to)
            try:
                with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
            except OSError as e:
                print(f"Error writing commit history export: {e}", file=sys.stderr)
                sys.exit(1)
            print(f"Wrote commit history export to {out_path}")

    file_commits = defaultdict(set)   # file -> set of commit hashes
    commit_messages = {}              # commit_hash -> message
    commit_authors = {}               # commit_hash -> author name
    commit_dates = {}                 # commit_hash -> date string

    file_additions = Counter()        # file -> total lines added
    file_deletions = Counter()        # file -> total lines deleted
    commit_additions = Counter()      # commit_hash -> total lines added
    commit_deletions = Counter()      # commit_hash -> total lines deleted

    if exclude_paths is None:
        exclude_paths = []
    
    # Normalize exclude paths
    exclude_normalized = [ex.strip().lstrip('./') for ex in exclude_paths if ex.strip()]

    lines = content.split('\n')
    i = 0
    current_commit = None
    
    while i < len(lines):
        line = lines[i]
        
        if line.startswith('commit '):
            current_commit = line.split()[1]
            commit_messages[current_commit] = ""
            i += 1
            
            # parse headers
            while i < len(lines) and not (lines[i].startswith('    ') or lines[i].strip() == '' or '\t' in lines[i]):
                if lines[i].startswith('Author:'):
                    author_match = re.match(r'^Author:\s+(.+?)(?:\s+<.*>)?$', lines[i])
                    if author_match:
                        commit_authors[current_commit] = author_match.group(1).strip()
                elif lines[i].startswith('Date:'):
                    date_match = re.match(r'^Date:\s+(.+)$', lines[i])
                    if date_match:
                        commit_dates[current_commit] = date_match.group(1).strip()
                i += 1
                
            # Skip blank line
            if i < len(lines) and lines[i].strip() == '':
                i += 1
                
            # Parse message
            msg_lines = []
            while i < len(lines) and (lines[i].startswith('    ') or lines[i].strip() == ''):
                if lines[i].startswith('    '):
                    msg_lines.append(lines[i].strip())
                i += 1
            commit_messages[current_commit] = ' '.join(msg_lines)
            continue
            
        # Parse numstat
        if current_commit and '\t' in line:
            parts = line.split('\t')
            if len(parts) == 3:
                adds_str, dels_str, filepath_str = parts
                
                # Exclude check
                if any(filepath_str.startswith(ex) for ex in exclude_normalized):
                    i += 1
                    continue
                    
                file_commits[filepath_str].add(current_commit)
                
                try:
                    adds = int(adds_str)
                except ValueError:
                    adds = 0
                try:
                    dels = int(dels_str)
                except ValueError:
                    dels = 0
                    
                file_additions[filepath_str] += adds
                file_deletions[filepath_str] += dels
                commit_additions[current_commit] += adds
                commit_deletions[current_commit] += dels
        
        i += 1

    # Build file commit counts
    file_commit_counts = Counter()
    for f, commits in file_commits.items():
        file_commit_counts[f] = len(commits)

    # Count unique commits per author
    author_unique = Counter()
    for commit_hash, author in commit_authors.items():
        author_unique[author] += 1

    return (file_commit_counts, author_unique, commit_messages, commit_dates, commit_authors, file_commits,
            file_additions, file_deletions, commit_additions, commit_deletions)


def parse_month_year(date_str):
    """Extract (YYYY, MM) tuple from a git date string like 'Thu Mar 18 14:42:51 2021 +0100'.

    Returns None if parsing fails.
    """
    month_map = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    }
    year_match = re.search(r'(\d{4})', date_str)
    month_match = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b', date_str, re.IGNORECASE)
    if year_match and month_match:
        return (year_match.group(1), month_map[month_match.group(1).lower()])
    return None


def extract_module(filepath):
    """Extract the module (directory path) from a file path by stripping the filename.

    Examples:
        'backend/Adacta.Commands/Logic/Calc.cs'        -> 'backend/Adacta.Commands/Logic'
        'frontend/src/app/plan/services/foo.ts'         -> 'frontend/src/app/plan/services'
        'frontend/src/app/account/index.html'           -> 'frontend/src/app/account'
        '.gitignore'                                    -> '(root)'
    """
    parts = filepath.split('/')
    if len(parts) == 1:
        return '(root)'
    return '/'.join(parts[:-1])


def parse_git_commit_date(date_str):
    """Parse git `Date:` header value, e.g. 'Thu Mar 18 14:42:51 2021 +0100'."""
    if not date_str:
        return None
    date_str = date_str.strip()
    try:
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y %z")
    except ValueError:
        pass
    return None


def parse_git_iso_date(date_str):
    """Parse `git log --format=%cI` output, e.g. '2021-03-18T14:42:51+01:00'."""
    if not date_str:
        return None
    date_str = date_str.strip()
    if date_str.endswith("Z"):
        try:
            return (
                datetime.strptime(date_str[:-1], "%Y-%m-%dT%H:%M:%S")
                .replace(tzinfo=timezone.utc)
            )
        except ValueError:
            return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _last_mod_datetime_for_file(repo_root, git_path, file_commits, commit_dates):
    """Latest commit date touching ``git_path`` from parsed history, else `git log -1`."""
    commits = file_commits.get(git_path)
    best = None
    if commits:
        for c in commits:
            ds = commit_dates.get(c)
            if not ds:
                continue
            dt = parse_git_commit_date(ds)
            if dt is not None and (best is None or dt > best):
                best = dt
    if best is not None:
        return best
    git_path_n = git_path.replace("\\", "/")
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", git_path_n],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return parse_git_iso_date(r.stdout.strip())
    except OSError:
        pass
    return None


def _line_count_at_head(repo_root, git_path):
    """Line count of file at HEAD; 0 if missing, binary, or unreadable."""
    git_path_n = git_path.replace("\\", "/")
    try:
        r = subprocess.run(
            ["git", "show", f"HEAD:{git_path_n}"],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if r.returncode != 0 or not r.stdout:
            return 0
        data = r.stdout
        if b"\x00" in data[:65536]:
            return 0
        text = data.decode("utf-8", errors="replace")
        if not text:
            return 0
        return len(text.splitlines())
    except OSError:
        return 0


def _oldest_commit_datetime(commit_dates):
    """Earliest commit timestamp in parsed history (for repository age)."""
    best = None
    for ds in commit_dates.values():
        dt = parse_git_commit_date(ds)
        if dt is None:
            continue
        if best is None or dt < best:
            best = dt
    return best


def _code_age_grouping_mode(repo_span_days):
    """Choose week / month / year buckets from repository span in days."""
    if repo_span_days is None:
        return "year"
    if repo_span_days < 183:  # < ~6 months
        return "week"
    if repo_span_days < 730:  # < 2 years
        return "month"
    return "year"


def _code_age_bucket_key(last_mod, now, mode):
    """Hashable bucket key for last-modification time under the given mode."""
    if last_mod.tzinfo is None:
        last_mod = last_mod.replace(tzinfo=timezone.utc)
    else:
        last_mod = last_mod.astimezone(timezone.utc)

    if mode == "week":
        y, w, _ = last_mod.isocalendar()
        return ("week", y, w)
    if mode == "month":
        return ("month", last_mod.year, last_mod.month)
    # year: floor years since last change, cap at 24 (label 24+)
    delta = now - last_mod
    years = max(0.0, delta.total_seconds() / (365.25 * 24 * 3600.0))
    b = min(int(years), 24)
    return ("year", b)


def _code_age_bucket_label(key):
    """Human-readable label for a bucket key."""
    kind = key[0]
    if kind == "week":
        _, y, w = key
        return f"ISO week {y}-W{w:02d} (last change)"
    if kind == "month":
        _, y, m = key
        return f"{y}-{m:02d} (last change)"
    if kind == "year":
        _, b = key
        if b < 24:
            return f"{b}–{b + 1} years since last change"
        return "24+ years since last change"
    return str(key)


def _sort_code_age_bucket_keys(keys):
    """Chronological order: oldest periods first."""

    def sk(k):
        if k[0] == "week":
            return (0, k[1], k[2])
        if k[0] == "month":
            return (1, k[1], k[2])
        if k[0] == "year":
            return (2, k[1])
        return (3, str(k))

    return sorted(keys, key=sk)


def compute_code_age_by_lines(
    repo_root,
    file_commits,
    commit_dates,
    exclude_paths,
    top_modules_per_bucket=5,
):
    """Distribute current line counts at HEAD into age buckets.

    Grouping depends on **repository age** (oldest commit in parsed history → now):

    - **< ~6 months**: buckets by **ISO week** of last file change.
    - **6 months … < 2 years**: buckets by **calendar month** of last file change.
    - **≥ 2 years**: buckets by **years since last change**, from 0–1y … 23–24y, then **24+y**.

    Approximation: all lines in a file inherit the **latest** commit date that touched
    that file in the parsed (non-merge) history. This is not per-line `git blame`.

    For each bucket, the top ``top_modules_per_bucket`` modules (directory path without
    filename) by line count in that bucket are attached as ``top_modules``.

    Returns dict with ``grouping_mode``, ``repo_span_days``, ``buckets`` (each with
    ``label``, ``lines``, ``pct``, ``top_modules``), etc.
    """
    root = os.path.abspath(repo_root)
    exclude_normalized = [ex.strip().lstrip("./") for ex in (exclude_paths or []) if ex.strip()]
    now = datetime.now(timezone.utc)

    oldest = _oldest_commit_datetime(commit_dates)
    repo_span_days = None
    oldest_iso = None
    if oldest is not None:
        o = oldest if oldest.tzinfo else oldest.replace(tzinfo=timezone.utc)
        o = o.astimezone(timezone.utc)
        oldest_iso = o.isoformat()
        repo_span_days = (now - o).days

    mode = _code_age_grouping_mode(repo_span_days)

    try:
        ls = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError) as e:
        return {
            "error": str(e),
            "total_lines": 0,
            "buckets": [],
            "unknown_lines": 0,
            "grouping_mode": mode,
            "repo_span_days": repo_span_days,
        }

    paths = [p.strip() for p in ls.stdout.splitlines() if p.strip()]
    bucket_lines = Counter()
    bucket_module_lines = defaultdict(Counter) if top_modules_per_bucket else None
    unknown_lines = 0
    total_lines = 0

    for git_path in paths:
        if any(git_path.startswith(ex) or git_path == ex.rstrip("/") for ex in exclude_normalized):
            continue
        lines = _line_count_at_head(root, git_path)
        if lines <= 0:
            continue
        total_lines += lines
        last_mod = _last_mod_datetime_for_file(root, git_path, file_commits, commit_dates)
        if last_mod is None:
            unknown_lines += lines
            continue
        key = _code_age_bucket_key(last_mod, now, mode)
        bucket_lines[key] += lines
        if bucket_module_lines is not None:
            module = extract_module(git_path.replace("\\", "/"))
            bucket_module_lines[key][module] += lines

    sorted_keys = _sort_code_age_bucket_keys(bucket_lines.keys())
    buckets = []
    for key in sorted_keys:
        ln = bucket_lines[key]
        pct = (100.0 * ln / total_lines) if total_lines > 0 else 0.0
        entry = {
            "label": _code_age_bucket_label(key),
            "lines": ln,
            "pct": round(pct, 1),
        }
        if (
            top_modules_per_bucket
            and top_modules_per_bucket > 0
            and ln > 0
            and bucket_module_lines is not None
        ):
            mods = bucket_module_lines[key].most_common(top_modules_per_bucket)
            entry["top_modules"] = [
                {
                    "module": name,
                    "lines": mlines,
                    "pct_of_bucket": round(100.0 * mlines / ln, 1) if ln else 0.0,
                }
                for name, mlines in mods
            ]
        else:
            entry["top_modules"] = []
        buckets.append(entry)

    unk_pct = (100.0 * unknown_lines / total_lines) if total_lines > 0 else 0.0
    return {
        "total_lines": total_lines,
        "unknown_lines": unknown_lines,
        "unknown_pct": round(unk_pct, 1),
        "buckets": buckets,
        "reference_time_utc": now.isoformat(),
        "grouping_mode": mode,
        "repo_span_days": repo_span_days,
        "oldest_commit_utc": oldest_iso,
    }


def categorize_commit(message):
    """Categorize a commit message into: bug_fix, feature, refactoring, or other.

    Uses keyword pattern matching with priority: bug > feature > refactoring > other.
    When both bug and feature keywords appear, the one appearing first wins.
    """
    msg_lower = message.lower()

    # Bug fix patterns
    bug_patterns = [
        r'\bfix(ed|es|ing)?\b', r'\bbug(fix|s)?\b', r'\bhotfix\b',
        r'\bpatch(ed|es|ing)?\b', r'\bcorrect(ed|s|ing|ion)?\b',
        r'\bsolve[ds]?\b', r'\bresolve[ds]?\b', r'\brepair\b',
        r'\bissue\b', r'\berror\b', r'\bcrash\b', r'\bbroken\b',
        r'\bfailing\b', r'\bfailed\b',
    ]

    # Feature patterns
    feature_patterns = [
        r'\badd(ed|s|ing)?\b', r'\bnew\b', r'\bimplement(ed|s|ing|ation)?\b',
        r'\bfeature\b', r'\bcreate[ds]?\b', r'\bintroduc(e|ed|ing)\b',
        r'\bsupport(s|ed|ing)?\b', r'\benable[ds]?\b',
        r'\binitial\b', r'\bsetup\b', r'\bset up\b',
    ]

    # Refactoring patterns
    refactor_patterns = [
        r'\brefactor(ed|s|ing)?\b', r'\brefacor(ed|s|ing)?\b',
        r'\bclean(ed|s|ing|up)?\b', r'\brenam(e|ed|ing)\b',
        r'\brestructur(e|ed|ing)\b', r'\breorganiz(e|ed|ing)\b',
        r'\bextract(ed|s|ing)?\b', r'\bsimplif(y|ied|ying)\b',
        r'\boptimiz(e|ed|ing|ation)\b', r'\bperformance\b',
        r'\bmoderniz(e|ed|ing)\b', r'\bmov(e|ed|ing)\b',
        r'\bmigrat(e|ed|ing|ion)\b', r'\bupgrad(e|ed|ing)\b',
        r'\bremov(e|ed|ing)\b',
    ]

    is_bug = any(re.search(p, msg_lower) for p in bug_patterns)
    is_feature = any(re.search(p, msg_lower) for p in feature_patterns)
    is_refactor = any(re.search(p, msg_lower) for p in refactor_patterns)

    if is_bug and not is_feature:
        return 'bug_fix'
    if is_bug and is_feature:
        # Disambiguate: whichever keyword appears first wins
        bug_pos = min(
            (m.start() for p in bug_patterns for m in [re.search(p, msg_lower)] if m),
            default=999,
        )
        feat_pos = min(
            (m.start() for p in feature_patterns for m in [re.search(p, msg_lower)] if m),
            default=999,
        )
        return 'bug_fix' if bug_pos <= feat_pos else 'feature'
    if is_feature:
        return 'feature'
    if is_refactor:
        return 'refactoring'

    return 'other'


def main():
    parser = argparse.ArgumentParser(
        description="Analyze git repository commit history (live git log or a saved export)."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Git repository root to analyze (default: current directory). Used as cwd for git log.",
    )
    parser.add_argument(
        "--commit-history",
        "-H",
        metavar="FILE",
        default=None,
        help=(
            "Read history from FILE (same format as `git log --numstat --no-merges`) "
            "instead of running git."
        ),
    )
    parser.add_argument(
        "--export-commit-history",
        "-E",
        nargs="?",
        const="commit-history.txt",
        default=None,
        metavar="FILE",
        help=(
            "After fetching from git, write the log to FILE (default: commit-history.txt). "
            "Cannot be used with --commit-history."
        ),
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Paths or prefixes to exclude (e.g. frontend/src/lib)",
    )
    parser.add_argument(
        "--no-code-age",
        action="store_true",
        help=(
            "Skip the code-age table (lines at HEAD by last commit date). "
            "Saves time on very large repositories."
        ),
    )
    parser.add_argument(
        "--code-age-top-modules",
        type=int,
        default=5,
        metavar="N",
        help=(
            "For each code-age bucket, list the top N modules (directory path, no filename) "
            "by lines in that bucket. Use 0 to disable. Default: 5."
        ),
    )
    args = parser.parse_args()

    if args.commit_history and args.export_commit_history:
        parser.error(
            "--export-commit-history cannot be used with --commit-history "
            "(use git in PATH to produce an export)."
        )

    if args.exclude:
        print(f"Excluding paths starting with: {', '.join(args.exclude)}")

    (file_commit_counts, author_commits, commit_messages, commit_dates, commit_authors, file_commits,
     file_additions, file_deletions, commit_additions, commit_deletions) = (
        parse_commit_history(
            exclude_paths=args.exclude,
            repo_path=args.path,
            commit_history_file=args.commit_history,
            export_commit_history_to=args.export_commit_history,
        )
    )

    total_unique_commits = len(commit_messages)
    print(f"\nTotal unique commits: {total_unique_commits}")
    print(f"Total unique files: {len(file_commit_counts)}")

    # === TOP 20 MOST FREQUENTLY CHANGED FILES (BY COMMITS) ===
    print("\n" + "=" * 80)
    print("TOP 20 MOST FREQUENTLY CHANGED FILES (BY COMMITS)")
    print("=" * 80)
    print(f"{'Rank':<6}{'Commits':<10}{'File'}")
    print("-" * 80)
    for rank, (filename, count) in enumerate(file_commit_counts.most_common(20), 1):
        print(f"{rank:<6}{count:<10}{filename}")

    # === TOP 20 MOST FREQUENTLY CHANGED FILES (BY LINES OF CODE) ===
    print("\n" + "=" * 80)
    print("TOP 20 MOST FREQUENTLY CHANGED FILES (BY LINES OF CODE)")
    print("=" * 80)
    print(f"{'Rank':<6}{'Total L/C':<12}{'Added':<10}{'Deleted':<10}{'File'}")
    print("-" * 80)
    
    files_by_loc = []
    for filename in file_commit_counts.keys():
        adds = file_additions[filename]
        dels = file_deletions[filename]
        total = adds + dels
        if total > 0:
            files_by_loc.append((filename, total, adds, dels))
            
    files_by_loc.sort(key=lambda x: x[1], reverse=True)
    
    for rank, (filename, total, adds, dels) in enumerate(files_by_loc[:20], 1):
        print(f"{rank:<6}{total:<12}{'+'+str(adds):<10}{'-'+str(dels):<10}{filename}")

    # === COMMIT CATEGORIZATION ===
    print("\n" + "=" * 80)
    print("COMMIT CATEGORIZATION")
    print("=" * 80)

    categories = Counter()
    category_examples = defaultdict(list)

    for commit_hash, message in commit_messages.items():
        cat = categorize_commit(message)
        categories[cat] += 1
        if len(category_examples[cat]) < 3:
            category_examples[cat].append(message[:100])

    total = sum(categories.values())
    for cat in ['feature', 'bug_fix', 'refactoring', 'other']:
        count = categories.get(cat, 0)
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {cat:<20} {count:>6} commits ({pct:>5.1f}%)")
        for ex in category_examples.get(cat, []):
            print(f"      Example: {ex}")

    print(f"\n  {'TOTAL':<20} {total:>6} commits")

    # === MOST POPULAR CODERS ===
    print("\n" + "=" * 80)
    print("MOST POPULAR CODERS (by unique commits)")
    print("=" * 80)
    print(f"{'Rank':<6}{'Commits':<10}{'Percentage':<12}{'Author'}")
    print("-" * 80)
    total_author = sum(author_commits.values())
    for rank, (author, count) in enumerate(author_commits.most_common(20), 1):
        pct = (count / total_author * 100) if total_author > 0 else 0
        print(f"{rank:<6}{count:<10}{pct:>5.1f}%       {author}")

    # === YEARLY COMMIT DISTRIBUTION ===
    print("\n" + "=" * 80)
    print("COMMITS BY YEAR")
    print("=" * 80)
    year_counts = Counter()
    yearly_adds = Counter()
    yearly_dels = Counter()
    
    for commit_hash, date_str in commit_dates.items():
        year_match = re.search(r'(\d{4})', date_str)
        if year_match:
            y = year_match.group(1)
            year_counts[y] += 1
            yearly_adds[y] += commit_additions[commit_hash]
            yearly_dels[y] += commit_deletions[commit_hash]

    print(f"  {'Year':<10}{'Commits':<10}{'Added':<10}{'Deleted':<10}{'Total L/C':<12}{'Trend'}")
    print("  " + "-" * 78)
    for year in sorted(year_counts.keys()):
        count = year_counts[year]
        adds = yearly_adds[year]
        dels = yearly_dels[year]
        total = adds + dels
        bar = '█' * (count // 5)
        print(f"  {year:<10}{count:<10}{'+'+str(adds):<10}{'-'+str(dels):<10}{total:<12}{bar}")

    # === CODE AGE (lines at HEAD, by years since last file change) ===
    code_age_data = None
    if not args.no_code_age:
        print("\n" + "=" * 80)
        print("CODE AGE (share of current lines by last modification)")
        print("=" * 80)
        code_age_data = compute_code_age_by_lines(
            args.path,
            file_commits,
            commit_dates,
            args.exclude,
            top_modules_per_bucket=args.code_age_top_modules,
        )
        if code_age_data.get("error"):
            print(f"  Could not compute code age: {code_age_data['error']}")
        elif code_age_data.get("total_lines", 0) == 0:
            print("  No lines counted (empty repo or no readable text files at HEAD).")
        else:
            gm = code_age_data.get("grouping_mode", "year")
            rsd = code_age_data.get("repo_span_days")
            if gm == "week":
                grp = (
                    "Grouping: ISO week of last file change "
                    "(repository history spans < 6 months)."
                )
            elif gm == "month":
                grp = (
                    "Grouping: calendar month of last file change "
                    "(6 months ≤ repository age < 2 years)."
                )
            else:
                grp = (
                    "Grouping: years since last change, buckets 0–1 … 23–24, then 24+ "
                    "(repository age ≥ 2 years)."
                )
            print(
                "\n  Each file's lines at HEAD are assigned to the latest commit that "
                "touched that file\n  (non-merge history). This approximates how stale "
                "code is; it is not per-line blame.\n"
            )
            print(f"  {grp}")
            if rsd is not None:
                print(f"  Repository span (oldest commit → now): {rsd} days.")
            print(
                f"\n  Reference time: {code_age_data['reference_time_utc']} (UTC)\n"
                f"  Total lines counted: {code_age_data['total_lines']:,}"
            )
            if code_age_data.get("unknown_lines", 0) > 0:
                print(
                    f"  Unknown age (no date): {code_age_data['unknown_lines']:,} lines "
                    f"({code_age_data.get('unknown_pct', 0):.1f}%)"
                )
            label_w = 40
            print(f"\n  {'Period':<{label_w}} {'Lines':>12} {'Share':>10}")
            print("  " + "-" * (label_w + 24))
            for row in code_age_data["buckets"]:
                bar = "█" * max(1, int(row["pct"] / 2)) if row["lines"] else ""
                lab = row["label"]
                if len(lab) > label_w:
                    lab = lab[: label_w - 1] + "…"
                print(
                    f"  {lab:<{label_w}} {row['lines']:>12,} "
                    f"{row['pct']:>9.1f}%  {bar}"
                )

            if args.code_age_top_modules > 0:
                print("\n" + "=" * 80)
                print("TOP MODULES PER CODE AGE BUCKET (by lines in bucket)")
                print("=" * 80)
                print(
                    "\n  Module = directory path without filename (same as COMMITS PER MODULE). "
                    "Share is % of lines within that bucket.\n"
                )
                for row in code_age_data["buckets"]:
                    tm = row.get("top_modules") or []
                    if not tm:
                        continue
                    hdr = (
                        f"  {row['label']}\n"
                        f"  Bucket: {row['lines']:,} lines ({row['pct']:.1f}% of repository)"
                    )
                    print(f"\n{hdr}")
                    print(f"  {'Rank':<6}{'Lines':>10}{'% of bucket':>14}  Module")
                    print("  " + "-" * 72)
                    for rank, m in enumerate(tm, 1):
                        mod = m["module"]
                        if len(mod) > 48:
                            mod = mod[:47] + "…"
                        print(
                            f"  {rank:<6}{m['lines']:>10,}{m['pct_of_bucket']:>13.1f}%  {mod}"
                        )

    # === BUG FIXES VS FEATURES OVER TIME (monthly) ===
    print("\n" + "=" * 80)
    print("BUG FIXES VS FEATURES/IMPROVEMENTS OVER TIME (by month)")
    print("=" * 80)

    # Categorize each commit and associate with its month
    monthly_bugs = Counter()     # (year, month) -> count
    monthly_features = Counter() # (year, month) -> count
    commit_categories = {}       # commit_hash -> category

    for commit_hash, message in commit_messages.items():
        cat = categorize_commit(message)
        commit_categories[commit_hash] = cat
        date_str = commit_dates.get(commit_hash, '')
        ym = parse_month_year(date_str)
        if ym:
            if cat == 'bug_fix':
                monthly_bugs[ym] += 1
            elif cat == 'feature':
                monthly_features[ym] += 1

    # Collect all months that have at least one bug or feature
    all_months = sorted(set(list(monthly_bugs.keys()) + list(monthly_features.keys())))

    month_names = {
        '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
        '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
        '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec',
    }

    print(f"  {'Month':<12} {'Bugs':>6} {'Features':>10} {'Bug Bar':<25} {'Feature Bar'}")
    print("  " + "-" * 78)

    monthly_timeline = []  # for JSON export
    for ym in all_months:
        year, month = ym
        bugs = monthly_bugs.get(ym, 0)
        features = monthly_features.get(ym, 0)
        bug_bar = '🔴' * bugs
        feat_bar = '🟢' * features
        label = f"{year}-{month_names[month]}"
        print(f"  {label:<12} {bugs:>6} {features:>10}   {bug_bar:<25} {feat_bar}")
        monthly_timeline.append({
            'year': year, 'month': month, 'label': label,
            'bug_fixes': bugs, 'features': features,
        })

    # Print yearly summary
    print(f"\n  {'--- Yearly Summary ---':^78}")
    print(f"  {'Year':<12} {'Bugs':>6} {'Features':>10} {'Ratio (B/F)':>12}")
    print("  " + "-" * 42)
    yearly_bugs = Counter()
    yearly_features = Counter()
    for ym, c in monthly_bugs.items():
        yearly_bugs[ym[0]] += c
    for ym, c in monthly_features.items():
        yearly_features[ym[0]] += c

    all_years = sorted(set(list(yearly_bugs.keys()) + list(yearly_features.keys())))
    for year in all_years:
        b = yearly_bugs.get(year, 0)
        f_count = yearly_features.get(year, 0)
        ratio = f"{b/f_count:.2f}" if f_count > 0 else 'N/A'
        print(f"  {year:<12} {b:>6} {f_count:>10} {ratio:>12}")

    # === COMMITS PER MODULE ===
    print("\n" + "=" * 80)
    print("COMMITS PER MODULE (based on path)")
    print("=" * 80)

    module_commits = defaultdict(set)  # module -> set of unique commit hashes
    for filepath, commits in file_commits.items():
        module = extract_module(filepath)
        module_commits[module].update(commits)

    # Sort by commit count descending
    module_counts = [(mod, len(commits)) for mod, commits in module_commits.items()]
    module_counts.sort(key=lambda x: x[1], reverse=True)

    total_module_commits = sum(c for _, c in module_counts)
    print(f"\n  Total unique modules: {len(module_counts)}")
    print(f"  {'Rank':<6}{'Commits':<10}{'Percentage':<12}{'Module'}")
    print("  " + "-" * 74)
    for rank, (mod, count) in enumerate(module_counts, 1):
        pct = (count / total_module_commits * 100) if total_module_commits > 0 else 0
        bar = '█' * (count // 10)
        print(f"  {rank:<6}{count:<10}{pct:>5.1f}%       {mod}  {bar}")

    # === BUG FIXES PER MODULE ===
    print("\n" + "=" * 80)
    print("BUG FIXES PER MODULE (Top 20)")
    print("=" * 80)
    
    module_bugs = []
    module_features = []
    
    for mod, commits in module_commits.items():
        b_count = sum(1 for c in commits if commit_categories.get(c) == 'bug_fix')
        f_count = sum(1 for c in commits if commit_categories.get(c) == 'feature')
        if b_count > 0:
            module_bugs.append((mod, b_count))
        if f_count > 0:
            module_features.append((mod, f_count))
            
    module_bugs.sort(key=lambda x: x[1], reverse=True)
    module_features.sort(key=lambda x: x[1], reverse=True)
    
    total_module_bugs = sum(c for _, c in module_bugs)
    print(f"\n  {'Rank':<6}{'Bug Fixes':<12}{'Percentage':<12}{'Module'}")
    print("  " + "-" * 74)
    for rank, (mod, count) in enumerate(module_bugs[:20], 1):
        pct = (count / total_module_bugs * 100) if total_module_bugs > 0 else 0
        bar = '█' * (count // 2)
        print(f"  {rank:<6}{count:<12}{pct:>5.1f}%       {mod}  {bar}")
        
    # === FEATURES PER MODULE ===
    print("\n" + "=" * 80)
    print("FEATURES PER MODULE (Top 20)")
    print("=" * 80)
    
    total_module_features = sum(c for _, c in module_features)
    print(f"\n  {'Rank':<6}{'Features':<12}{'Percentage':<12}{'Module'}")
    print("  " + "-" * 74)
    for rank, (mod, count) in enumerate(module_features[:20], 1):
        pct = (count / total_module_features * 100) if total_module_features > 0 else 0
        bar = '█' * (count // 2)
        print(f"  {rank:<6}{count:<12}{pct:>5.1f}%       {mod}  {bar}")

    # === EXPORT JSON ===
    results = {
        'total_unique_commits': total_unique_commits,
        'total_files': len(file_commit_counts),
        'top_20_files': file_commit_counts.most_common(20),
        'categories': dict(categories),
        'authors': author_commits.most_common(20),
        'year_distribution': dict(sorted(year_counts.items())),
        'monthly_bugs_vs_features': monthly_timeline,
        'modules': module_counts,
        'module_bugs': module_bugs,
        'module_features': module_features,
        'code_age_by_lines': code_age_data,
    }

    output_json = 'commit_analysis_results.json'
    with open(output_json, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_json}")


if __name__ == '__main__':
    main()
