"""Turn Roslyn oracle output for one file into the expected-values fixture used by
test_complexity_analysis.py (TestCSharpRoslynFixture).

    dotnet run tools/roslyn_check/Oracle.cs -- test_fixtures/csharp/OrderService.cs > /tmp/o.json
    python3 tools/roslyn_check/make_expected.py /tmp/o.json > test_fixtures/csharp/OrderService.expected.json
"""
import json
import sys

(f,) = json.load(open(sys.argv[1]))
expected = {
    "source": f["path"],
    "generated_by": "tools/roslyn_check/Oracle.cs (Roslyn syntax tree)",
    "file_cyclomatic": f["cc"],
    # Block-bodied members only: expression-bodied (=>) and abstract/interface
    # members are not reported as functions by the script, by design.
    "functions": [
        {"name": m["name"], "line": m["decl_line"], "cyclomatic": m["cc"], "cognitive": m["cog"]}
        for m in f["members"]
        if m["body"] == "block" and (m["kind"] != "local" or m.get("top_level"))
    ],
}
print(json.dumps(expected, indent=2))
