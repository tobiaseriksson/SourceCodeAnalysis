"""Compare complexity_analysis.py against the Roslyn oracle for C# files.

Usage:
    dotnet run tools/roslyn_check/Oracle.cs -- <root> > oracle.json
    python3 tools/roslyn_check/compare.py oracle.json <root> [--show N] [--detail]

Reports C# members the script does not detect (by kind), functions the script
reports where Roslyn has none, and per-function / per-file metric differences.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import complexity_analysis as ca  # noqa: E402

oracle_path, root = sys.argv[1], sys.argv[2]
show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 8
detail = "--detail" in sys.argv

oracle = {f["path"]: f for f in json.load(open(oracle_path))}

missed = collections.Counter()          # oracle kind/body not found by script
missed_ex = collections.defaultdict(list)
spurious = []                           # script functions with no oracle member
cc_diff, cog_diff = [], []
matched = 0
file_cc_diff = []
extra_totals = collections.Counter()
parse_err_files = 0
oracle_block_members = 0

for rel, o in sorted(oracle.items()):
    if o["parse_errors"]:
        parse_err_files += 1
    path = os.path.join(root, rel)
    fm = ca.analyze_file(path, rel)
    for k, v in o["extra"].items():
        extra_totals[k] += v

    # File-level CC (adjusting for constructs outside the definition is not done:
    # the oracle uses exactly the script's definition)
    if fm.cyclomatic != o["cc"]:
        file_cc_diff.append((rel, fm.cyclomatic, o["cc"]))

    members = [m for m in o["members"] if m["kind"] != "local" or m.get("top_level")]
    by_line = collections.defaultdict(list)
    for m in members:
        by_line[m["decl_line"]].append(m)
    used = set()
    for f in fm.function_metrics:
        cands = by_line.get(f.start_line, [])
        m = next((c for c in cands if id(c) not in used), None)
        if m is None:
            spurious.append((rel, f.start_line, f.name))
            continue
        used.add(id(m))
        matched += 1
        if f.cyclomatic != m["cc"]:
            cc_diff.append((rel, f.start_line, m["name"], f.cyclomatic, m["cc"]))
        if f.cognitive != m["cog"]:
            cog_diff.append((rel, f.start_line, m["name"], f.cognitive, m["cog"]))
    for m in members:
        if m["body"] == "block":
            oracle_block_members += 1
        if id(m) in used:
            continue
        key = f'{m["kind"]} ({m["body"]} body)'
        missed[key] += 1
        missed_ex[key].append((rel, m["decl_line"], m["name"]))

n_files = len(oracle)
print(f"Files: {n_files}   (files Roslyn reports syntax errors in: {parse_err_files})")
print(f"Block-bodied members (methods/ctors/operators/accessors/dtors): {oracle_block_members}")
print(f"Matched script functions: {matched}")
print()
print("NOT DETECTED by the script, by kind:")
for k, v in missed.most_common():
    print(f"  {v:6d}  {k}")
    for ex in missed_ex[k][:min(show, 3) if not detail else show]:
        print(f"            e.g. {ex[0]}:{ex[1]}  {ex[2]}")
print()
print(f"FALSE functions (script found, Roslyn has no member there): {len(spurious)}")
for s in spurious[:show]:
    print(f"            {s[0]}:{s[1]}  {s[2]}")
print()


def summarize(diffs, label):
    print(f"{label}: {len(diffs)} of {matched} matched functions differ")
    if diffs:
        deltas = collections.Counter(d[3] - d[4] for d in diffs)
        print("  script - roslyn delta histogram:", dict(sorted(deltas.items())))
        for d in diffs[:show]:
            print(f"            {d[0]}:{d[1]}  {d[2]}: script={d[3]} roslyn={d[4]}")
    print()


summarize(cc_diff, "Per-function CYCLOMATIC")
summarize(cog_diff, "Per-function COGNITIVE")
print(f"File-level CYCLOMATIC: {len(file_cc_diff)} of {n_files} files differ")
if file_cc_diff:
    deltas = [a - b for _, a, b in file_cc_diff]
    print(f"  total script={sum(a for _, a, _ in file_cc_diff)} roslyn={sum(b for _, _, b in file_cc_diff)} in those files;"
          f" over-count files={sum(d > 0 for d in deltas)} under-count files={sum(d < 0 for d in deltas)}")
    for d in sorted(file_cc_diff, key=lambda x: -abs(x[1] - x[2]))[:show]:
        print(f"            {d[0]}: script={d[1]} roslyn={d[2]}")
print()
print("Decision points OUTSIDE the script's CC definition (not counted by either):")
for k, v in extra_totals.most_common():
    if k in ("switch_expr_arms", "case_when_guards", "interp_ternary"):
        continue  # now part of the definition
    print(f"  {v:6d}  {k}")
