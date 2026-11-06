#!/usr/bin/env python3
"""
Test suite for complexity_analysis.py

Validates the three core metrics calculated by the analyzer:
  1. Cyclomatic Complexity  (McCabe, 1976)
  2. Cognitive Complexity   (SonarSource, 2023)
  3. Max Nesting Depth      (brace-depth)

References:
  - Cyclomatic:  https://jellyfish.co/library/cyclomatic-complexity/
                 CC = Decision Points + 1
  - Cognitive:   SonarSource "Cognitive Complexity" white paper (2023)
                 by G. Ann Campbell
  - Nesting:     Total brace depth (all braces, including class/try)

Prerequisites:
  - Python 3.6+
  - complexity_analysis.py must be in the same directory (or on PYTHONPATH)

How to run:
  From the project root, execute one of the following commands:

    # Run all tests (minimal output — only failures shown)
    python3 test_complexity_analysis.py

    # Run all tests with verbose output (shows each test name and result)
    python3 test_complexity_analysis.py -v
    python3 -m unittest test_complexity_analysis -v

    # Run a specific test class (e.g. only cyclomatic tests)
    python3 -m unittest test_complexity_analysis.TestCyclomaticIfElse -v
    python3 -m unittest test_complexity_analysis.TestCognitiveStructural -v
    python3 -m unittest test_complexity_analysis.TestNesting -v

    # Run a single test method
    python3 -m unittest test_complexity_analysis.TestIntegration.test_complex_method -v

    # Run with unittest discovery (finds all test_*.py in current dir)
    python3 -m unittest discover -v

  Test classes:
    Cyclomatic Complexity (34 tests):
      TestCyclomaticBaseline, TestCyclomaticIfElse,
      TestCyclomaticJellyfishExamples, TestCyclomaticLoops,
      TestCyclomaticSwitchCase, TestCyclomaticCatch,
      TestCyclomaticLogicalOperators, TestCyclomaticTernary,
      TestCyclomaticInstanceof, TestCyclomaticCSharpExtras,
      TestCyclomaticCombined

    Cognitive Complexity (30 tests):
      TestLogicalOperatorSequences, TestCognitiveBaseline,
      TestCognitiveStructural, TestCognitiveNesting,
      TestCognitiveHybrid, TestCognitiveLogicalOperatorsInContext,
      TestCognitiveIgnored, TestCognitiveTryNesting,
      TestCognitivePDFExamples

    Max Nesting Depth (9 tests):
      TestNesting

    Integration — all three metrics at once (6 tests):
      TestIntegration

    Python indentation analyzer & Go/Rust extras (6 tests):
      TestPythonIndentationMetrics, TestGoRustCyclomaticExtras

    String/comment cleaning, function detection, Vue/Svelte & new file types:
      TestCleanerLineAlignment, TestFunctionDetection, TestSingleFileComponents

    Fixes verified against Roslyn (the C# compiler), see tools/roslyn_check/:
      TestTernaryDetection, TestCatchDetection, TestParenlessConditions,
      TestCognitiveNestingRoles, TestBracelessBodies, TestMultiLineLogicalSequences,
      TestCSharpSwitchAndWhen, TestCSharpFunctionDetection, TestJsArrowFunctions,
      TestCSharpRoslynFixture

  Expected output (all tests passing):
    Ran 154 tests in 0.04s
    OK
"""

import sys
import unittest
from complexity_analysis import (
    FileMetrics,
    _analyze_cstyle,
    _analyze_indentation_based,
    _clean_cstyle_code,
    _count_logical_operator_sequences,
    _detect_lang,
    _extract_sfc_script,
    _analyze_functions,
    _find_function_boundaries,
    analyze_file,
    scan_project,
)


# ─── Helper ─────────────────────────────────────────────────────────────────

def analyze(code: str, lang: str = "cs"):
    """Analyze a code snippet and return (cyclomatic, cognitive, max_nesting)."""
    fm = FileMetrics("__test__", lang)
    fm = _analyze_cstyle(code, fm)
    return fm.cyclomatic, fm.cognitive, fm.max_nesting


def analyze_py(code: str):
    """Python / Ruby / R via indentation-based analyzer."""
    fm = FileMetrics("__test__", "py")
    fm = _analyze_indentation_based(code, fm)
    return fm.cyclomatic, fm.cognitive, fm.max_nesting


# ═══════════════════════════════════════════════════════════════════════════
#  CYCLOMATIC COMPLEXITY  (McCabe)
#  CC = Decision Points + 1
#  Decision points: if, else-if, while, for, foreach, case, catch,
#                   each &&, each ||, ternary ? :
#  NOT decision points: else, switch, try, finally, default, instanceof
# ═══════════════════════════════════════════════════════════════════════════


class TestCyclomaticBaseline(unittest.TestCase):
    """CC = 1 for straight-line code with no decisions."""

    def test_empty_body(self):
        cc, _, _ = analyze("int x = 1;")
        self.assertEqual(cc, 1)

    def test_assignments_only(self):
        cc, _, _ = analyze("int x = 1;\nint y = 2;\nint z = x + y;")
        self.assertEqual(cc, 1)

    def test_class_declaration_no_logic(self):
        cc, _, _ = analyze("public class Foo {\n  int x = 1;\n}")
        self.assertEqual(cc, 1)


class TestCyclomaticIfElse(unittest.TestCase):
    """if is a decision; else is NOT."""

    def test_single_if(self):
        cc, _, _ = analyze("if (x > 0) {\n  y = 1;\n}")
        self.assertEqual(cc, 2, "1 decision (if) + 1 = 2")

    def test_if_else(self):
        cc, _, _ = analyze("if (x > 0) {\n  y = 1;\n} else {\n  y = 2;\n}")
        self.assertEqual(cc, 2, "else is NOT a decision point")

    def test_if_elseif(self):
        cc, _, _ = analyze(
            "if (a) {\n  x=1;\n} else if (b) {\n  x=2;\n}")
        self.assertEqual(cc, 3, "2 decisions (if + else-if's if) + 1 = 3")

    def test_if_two_elseif_else(self):
        cc, _, _ = analyze(
            "if (a) { x=1; }\n"
            "else if (b) { x=2; }\n"
            "else if (c) { x=3; }\n"
            "else { x=4; }")
        self.assertEqual(cc, 4, "3 decisions + 1 = 4")


class TestCyclomaticJellyfishExamples(unittest.TestCase):
    """All three examples from the Jellyfish article."""

    def test_example1_multiple_conditions(self):
        """check_grade: if + 3 elif → CC=5"""
        code = (
            'if (score >= 90) {\n  grade = "A";\n}\n'
            'else if (score >= 80) {\n  grade = "B";\n}\n'
            'else if (score >= 70) {\n  grade = "C";\n}\n'
            'else if (score >= 60) {\n  grade = "D";\n}\n'
            'else {\n  grade = "F";\n}')
        cc, _, _ = analyze(code)
        self.assertEqual(cc, 5)

    def test_example2_loop_with_condition(self):
        """for + if → CC=3"""
        code = (
            "for (int i=0; i<n; i++) {\n"
            "  if (items[i] > 10) {\n    count++;\n  }\n}")
        cc, _, _ = analyze(code)
        self.assertEqual(cc, 3)

    def test_example3_nested_conditions(self):
        """if + nested if → CC=3"""
        code = (
            'if (role == "admin") {\n  access = true;\n} else {\n'
            '  if (level <= 1) {\n    access = true;\n  } else {\n'
            '    access = false;\n  }\n}')
        cc, _, _ = analyze(code)
        self.assertEqual(cc, 3)


class TestCyclomaticLoops(unittest.TestCase):

    def test_for(self):
        cc, _, _ = analyze("for (int i=0; i<n; i++) { x++; }")
        self.assertEqual(cc, 2)

    def test_while(self):
        cc, _, _ = analyze("while (x > 0) { x--; }")
        self.assertEqual(cc, 2)

    def test_foreach_cs(self):
        cc, _, _ = analyze("foreach (var item in list) { x++; }", lang="cs")
        self.assertEqual(cc, 2)

    def test_nested_for_while(self):
        cc, _, _ = analyze(
            "for (int i=0; i<n; i++) {\n  while (y>0) { y--; }\n}")
        self.assertEqual(cc, 3, "2 loops + 1 = 3")


class TestCyclomaticSwitchCase(unittest.TestCase):

    def test_two_cases(self):
        cc, _, _ = analyze(
            "switch (x) {\n  case 1: break;\n  case 2: break;\n}")
        self.assertEqual(cc, 3, "2 cases + 1 = 3")

    def test_three_cases(self):
        cc, _, _ = analyze(
            "switch (x) {\n  case 1: break;\n  case 2: break;\n"
            "  case 3: break;\n}")
        self.assertEqual(cc, 4)

    def test_default_not_counted(self):
        cc, _, _ = analyze(
            "switch (x) {\n  case 1: break;\n  default: break;\n}")
        self.assertEqual(cc, 2, "default is NOT a decision")


class TestCyclomaticCatch(unittest.TestCase):

    def test_single_catch(self):
        cc, _, _ = analyze(
            "try { x=1; } catch (Exception e) { y=2; }")
        self.assertEqual(cc, 2)

    def test_two_catches(self):
        cc, _, _ = analyze(
            "try { x=1; }\n"
            "catch (ArgumentException e) { y=2; }\n"
            "catch (Exception e) { z=3; }")
        self.assertEqual(cc, 3)

    def test_finally_not_counted(self):
        cc, _, _ = analyze(
            "try { x=1; } catch (Exception e) { y=2; } finally { z=3; }")
        self.assertEqual(cc, 2, "finally is NOT a decision")

    def test_try_alone(self):
        cc, _, _ = analyze("try { x=1; }")
        self.assertEqual(cc, 1, "try alone has no decisions")


class TestCyclomaticLogicalOperators(unittest.TestCase):
    """Each && and || occurrence is a separate decision point."""

    def test_single_and(self):
        cc, _, _ = analyze("if (a && b) { x=1; }")
        self.assertEqual(cc, 3, "if + && = 2 decisions + 1")

    def test_double_and(self):
        cc, _, _ = analyze("if (a && b && c) { x=1; }")
        self.assertEqual(cc, 4, "if + 2×&& = 3 decisions + 1")

    def test_single_or(self):
        cc, _, _ = analyze("if (a || b) { x=1; }")
        self.assertEqual(cc, 3)

    def test_mixed_and_or(self):
        cc, _, _ = analyze("if (a && b || c) { x=1; }")
        self.assertEqual(cc, 4, "if + && + || = 3 decisions + 1")


class TestCyclomaticTernary(unittest.TestCase):

    def test_simple_ternary(self):
        cc, _, _ = analyze("int x = a > 0 ? 1 : 0;")
        self.assertEqual(cc, 2)

    def test_ternary_inside_if(self):
        cc, _, _ = analyze("if (a) {\n  int x = b > 0 ? 1 : 0;\n}")
        self.assertEqual(cc, 3)


class TestCyclomaticInstanceof(unittest.TestCase):
    """instanceof is NOT a decision point."""

    def test_if_instanceof(self):
        cc, _, _ = analyze(
            "if (obj instanceof String) { x=1; }", lang="java")
        self.assertEqual(cc, 2, "only the if is a decision")

    def test_two_if_instanceof(self):
        cc, _, _ = analyze(
            "if (obj instanceof String) { x=1; }\n"
            "else if (obj instanceof Integer) { x=2; }", lang="java")
        self.assertEqual(cc, 3, "2 ifs, instanceof NOT counted")


class TestCyclomaticCSharpExtras(unittest.TestCase):

    def test_null_coalescing(self):
        cc, _, _ = analyze("var x = a ?? b;", lang="cs")
        self.assertEqual(cc, 2, "?? is a decision point in CC")

    def test_when_filter(self):
        cc, _, _ = analyze(
            "try { x=1; }\n"
            "catch (Exception e) when (e.Code > 0) { y=2; }", lang="cs")
        self.assertEqual(cc, 3, "catch + when = 2 decisions + 1")


class TestCyclomaticCombined(unittest.TestCase):

    def test_for_if_and_elseif(self):
        """for + if(&&) + else-if = 4 decisions → CC=5"""
        code = (
            "for (int i=0; i<n; i++) {\n"
            "  if (items[i] > 0 && items[i] < 100) {\n"
            "    process(items[i]);\n"
            "  } else if (items[i] >= 100) {\n"
            "    skip(items[i]);\n"
            "  }\n}")
        cc, _, _ = analyze(code)
        self.assertEqual(cc, 5)


# ═══════════════════════════════════════════════════════════════════════════
#  COGNITIVE COMPLEXITY  (SonarSource 2023)
#
#  Increment categories:
#    Structural:   +1 + nesting_level  (if, for, while, switch, catch, ternary)
#    Hybrid:       +1 only             (else, else if)
#    Fundamental:  +1 per sequence     (logical operator sequences)
#    Ignored:      try, finally, synchronized, ??, ?.
#
#  Reference: Cognitive_Complexity_Sonar_Guide_2023.pdf
# ═══════════════════════════════════════════════════════════════════════════


class TestLogicalOperatorSequences(unittest.TestCase):
    """Fundamental increments: count by SEQUENCE, not per operator."""

    def test_single_and(self):
        self.assertEqual(_count_logical_operator_sequences("a && b"), 1)

    def test_multiple_same_and(self):
        self.assertEqual(
            _count_logical_operator_sequences("a && b && c"), 1,
            "same operator = 1 sequence")

    def test_multiple_same_or(self):
        self.assertEqual(
            _count_logical_operator_sequences("a || b || c"), 1)

    def test_mixed_and_or(self):
        self.assertEqual(
            _count_logical_operator_sequences("a && b || c"), 2,
            "&& then || = 2 sequences")

    def test_three_alternating(self):
        self.assertEqual(
            _count_logical_operator_sequences("a && b || c && d"), 3,
            "&&, ||, && = 3 sequences")

    def test_no_operators(self):
        self.assertEqual(
            _count_logical_operator_sequences("x = 1 + 2"), 0)

    def test_four_same(self):
        self.assertEqual(
            _count_logical_operator_sequences("a && b && c && d && e"), 1)


class TestCognitiveBaseline(unittest.TestCase):

    def test_straight_line(self):
        _, cog, _ = analyze("int x = 1;\nint y = 2;")
        self.assertEqual(cog, 0)


class TestCognitiveStructural(unittest.TestCase):
    """Structural: +1 + nesting_level."""

    def test_if_at_level_0(self):
        _, cog, _ = analyze("if (a) {\n  x = 1;\n}")
        self.assertEqual(cog, 1, "+1 + 0 = 1")

    def test_for_at_level_0(self):
        _, cog, _ = analyze("for (int i=0; i<n; i++) {\n  x++;\n}")
        self.assertEqual(cog, 1)

    def test_while_at_level_0(self):
        _, cog, _ = analyze("while (x > 0) {\n  x--;\n}")
        self.assertEqual(cog, 1)

    def test_switch_at_level_0(self):
        """switch is structural; case labels are NOT counted."""
        _, cog, _ = analyze(
            "switch (x) {\n  case 1: break;\n  case 2: break;\n}")
        self.assertEqual(cog, 1, "only the switch itself is counted")

    def test_catch_at_level_0(self):
        """catch is structural (try is ignored)."""
        _, cog, _ = analyze(
            "try {\n  x = 1;\n} catch (Exception e) {\n  y = 2;\n}")
        self.assertEqual(cog, 1)

    def test_ternary_at_level_0(self):
        _, cog, _ = analyze("int x = a > 0 ? 1 : 0;")
        self.assertEqual(cog, 1)

    def test_foreach_at_level_0(self):
        _, cog, _ = analyze(
            "foreach (var item in list) {\n  x++;\n}", lang="cs")
        self.assertEqual(cog, 1)


class TestCognitiveNesting(unittest.TestCase):
    """Structural increments increase with nesting depth."""

    def test_if_inside_for(self):
        """for=+1(nest=0), if=+1+1(nest=1) = 3"""
        _, cog, _ = analyze(
            "for (int i=0; i<n; i++) {\n"
            "  if (a) {\n    x=1;\n  }\n}")
        self.assertEqual(cog, 3)

    def test_three_levels_deep(self):
        """for=+1, while=+2, if=+3 = 6"""
        _, cog, _ = analyze(
            "for (int i=0; i<n; i++) {\n"
            "  while (j>0) {\n"
            "    if (a) {\n      x=1;\n    }\n"
            "  }\n}")
        self.assertEqual(cog, 6)

    def test_ternary_inside_if(self):
        """if=+1(nest=0), ternary=+1+1(nest=1) = 3"""
        _, cog, _ = analyze(
            "if (cond) {\n  int x = a > 0 ? 1 : 0;\n}")
        self.assertEqual(cog, 3)

    def test_catch_inside_if(self):
        """if=+1(nest=0), catch=+1+1(nest=1) = 3"""
        _, cog, _ = analyze(
            "if (a) {\n  try {\n    x=1;\n"
            "  } catch (Exception e) {\n    y=2;\n  }\n}")
        self.assertEqual(cog, 3)


class TestCognitiveHybrid(unittest.TestCase):
    """Hybrid (else, else-if): +1 only, no nesting penalty."""

    def test_if_else(self):
        """if=+1, else=+1 (hybrid) = 2"""
        _, cog, _ = analyze(
            "if (a) {\n  x=1;\n} else {\n  x=2;\n}")
        self.assertEqual(cog, 2)

    def test_if_elseif_else(self):
        """if=+1, else if=+1, else=+1 = 3"""
        _, cog, _ = analyze(
            "if (a) {\n  x=1;\n} else if (b) {\n  x=2;\n"
            "} else {\n  x=3;\n}")
        self.assertEqual(cog, 3)

    def test_many_elseif_flat(self):
        """if + 3 else-if + else = 5 (all +1, no nesting penalty)."""
        _, cog, _ = analyze(
            "if (a) { x=1; }\n"
            "else if (b) { x=2; }\n"
            "else if (c) { x=3; }\n"
            "else if (d) { x=4; }\n"
            "else { x=5; }")
        self.assertEqual(cog, 5)

    def test_elseif_no_nesting_penalty_inside_for(self):
        """for=+1, if=+2(nest=1), else if=+1(hybrid), else=+1(hybrid) = 5"""
        _, cog, _ = analyze(
            "for (int i=0; i<n; i++) {\n"
            "  if (a) {\n    x=1;\n"
            "  } else if (b) {\n    x=2;\n"
            "  } else {\n    x=3;\n  }\n}")
        self.assertEqual(cog, 5)


class TestCognitiveLogicalOperatorsInContext(unittest.TestCase):
    """Fundamental: logical operator sequences (not per-occurrence)."""

    def test_if_single_and(self):
        """if=+1, &&seq=+1 = 2"""
        _, cog, _ = analyze("if (a && b) {\n  x=1;\n}")
        self.assertEqual(cog, 2)

    def test_if_double_and(self):
        """if=+1, &&seq=+1 (still one sequence) = 2"""
        _, cog, _ = analyze("if (a && b && c) {\n  x=1;\n}")
        self.assertEqual(cog, 2)

    def test_if_mixed_and_or(self):
        """if=+1, &&seq=+1, ||seq=+1 = 3"""
        _, cog, _ = analyze("if (a && b || c) {\n  x=1;\n}")
        self.assertEqual(cog, 3)

    def test_standalone_logical_expression(self):
        """Just a logical assignment, no if: only the sequence is counted."""
        _, cog, _ = analyze("bool x = a && b;")
        self.assertEqual(cog, 1)


class TestCognitiveIgnored(unittest.TestCase):
    """Constructs that must NOT increment cognitive score."""

    def test_try_ignored(self):
        _, cog, _ = analyze("try {\n  x = 1;\n}")
        self.assertEqual(cog, 0)

    def test_finally_ignored(self):
        _, cog, _ = analyze(
            "try {\n  x=1;\n} catch (Exception e) {\n  y=2;\n"
            "} finally {\n  z=3;\n}")
        self.assertEqual(cog, 1, "only catch counted")

    def test_null_coalescing_ignored(self):
        """?? is shorthand and should NOT be counted for cognitive."""
        _, cog, _ = analyze("var x = a ?? b;", lang="cs")
        self.assertEqual(cog, 0)

    def test_null_coalescing_inside_if(self):
        _, cog, _ = analyze(
            "if (a != null) {\n  var x = a ?? b;\n}", lang="cs")
        self.assertEqual(cog, 1, "only the if is counted")

    def test_synchronized_ignored_java(self):
        _, cog, _ = analyze(
            "synchronized (lock) {\n  x = 1;\n}", lang="java")
        self.assertEqual(cog, 0)


class TestCognitiveTryNesting(unittest.TestCase):
    """try/finally don't increase nesting level for cognitive scoring."""

    def test_catch_after_try(self):
        """catch should be at nesting 0 (try doesn't increase nesting)."""
        _, cog, _ = analyze(
            "try {\n  x=1;\n} catch (Exception e) {\n  y=2;\n}")
        self.assertEqual(cog, 1, "catch at nesting 0 = +1")

    def test_if_inside_try_then_catch(self):
        """if inside try is at nesting 0 (try doesn't add cognitive nesting).
        catch is also at nesting 0 after try closes."""
        _, cog, _ = analyze(
            "try {\n  if (a) {\n    x=1;\n  }\n"
            "} catch (Exception e) {\n  y=2;\n}")
        self.assertEqual(cog, 2, "if(+1) + catch(+1) = 2")


class TestCognitivePDFExamples(unittest.TestCase):
    """Examples derived from the SonarSource Cognitive Complexity white paper."""

    def test_pdf_for_while_if(self):
        """From the PDF:
        for (nest=0): +1
        while (nest=1): +1+1 = 2
        if (nest=2): +1+2 = 3
        Total = 6"""
        _, cog, _ = analyze(
            "for (int i=0; i<n; i++) {\n"
            "  while (j > 0) {\n"
            "    if (a) {\n      x = 1;\n    }\n"
            "  }\n}")
        self.assertEqual(cog, 6)

    def test_pdf_elseif_after_nested_if(self):
        """From the PDF: else-if after a deeply nested if gets +1 only.
        for=+1, while=+2, if=+3, else if=+1 = 7"""
        _, cog, _ = analyze(
            "for (int i=0; i<n; i++) {\n"
            "  while (j > 0) {\n"
            "    if (a) {\n      x = 1;\n"
            "    } else if (b) {\n      x = 2;\n"
            "    }\n  }\n}")
        self.assertEqual(cog, 7)


# ═══════════════════════════════════════════════════════════════════════════
#  MAX NESTING DEPTH
#  Tracks total brace depth (all braces, including class/try/namespace).
# ═══════════════════════════════════════════════════════════════════════════


class TestNesting(unittest.TestCase):

    def test_no_braces(self):
        _, _, nest = analyze("int x = 1;")
        self.assertEqual(nest, 0)

    def test_single_brace_level(self):
        _, _, nest = analyze("if (a) {\n  x = 1;\n}")
        self.assertEqual(nest, 1)

    def test_two_levels(self):
        _, _, nest = analyze(
            "if (a) {\n  if (b) {\n    x = 1;\n  }\n}")
        self.assertEqual(nest, 2)

    def test_three_levels(self):
        _, _, nest = analyze(
            "for (int i=0; i<n; i++) {\n"
            "  while (j>0) {\n"
            "    if (a) {\n      x=1;\n    }\n"
            "  }\n}")
        self.assertEqual(nest, 3)

    def test_class_brace_counts(self):
        """Class braces DO count toward max_nesting (total brace depth)."""
        _, _, nest = analyze(
            "public class Foo {\n"
            "  void Bar() {\n    int x = 1;\n  }\n}")
        self.assertEqual(nest, 2)

    def test_try_brace_counts(self):
        """try braces count toward max_nesting even though they don't
        increase cognitive nesting."""
        _, _, nest = analyze(
            "try {\n  if (a) {\n    x=1;\n  }\n}")
        self.assertEqual(nest, 2)

    def test_sequential_blocks_dont_accumulate(self):
        """Sequential (not nested) blocks should not accumulate."""
        _, _, nest = analyze(
            "if (a) {\n  x=1;\n}\nif (b) {\n  y=2;\n}")
        self.assertEqual(nest, 1)

    def test_deeply_nested(self):
        _, _, nest = analyze(
            "if (a) {\n"
            "  for (int i=0; i<n; i++) {\n"
            "    while (j > 0) {\n"
            "      switch (x) {\n"
            "        case 1:\n"
            "          if (b) {\n            z=1;\n          }\n"
            "          break;\n"
            "      }\n"
            "    }\n"
            "  }\n}")
        self.assertEqual(nest, 5)

    def test_namespace_class_method(self):
        """Typical C# structure: namespace → class → method → logic."""
        _, _, nest = analyze(
            "namespace Foo {\n"
            "  public class Bar {\n"
            "    public void Baz() {\n"
            "      if (a) {\n        x=1;\n      }\n"
            "    }\n"
            "  }\n}", lang="cs")
        self.assertEqual(nest, 4)

    def test_braces_in_strings_ignored(self):
        """Curly braces inside strings must be completely ignored for nesting depth."""
        code = (
            "if (a) {\n"
            "  string s1 = \"{\";\n"
            "  string s2 = \"}\";\n"
            "  string s3 = \"nested { braces } here\";\n"
            "}"
        )
        _, _, nest = analyze(code, lang="js")
        self.assertEqual(nest, 1, "braces in strings should not affect nesting")

    def test_braces_in_comments_ignored(self):
        """Curly braces inside single-line and multi-line comments must be ignored."""
        code = (
            "if (a) {\n"
            "  // a comment with }\n"
            "  /* multi line\n"
            "     comment with {\n"
            "  */\n"
            "}"
        )
        _, _, nest = analyze(code, lang="js")
        self.assertEqual(nest, 1, "braces in comments should not affect nesting")

    def test_json_literal_ignored(self):
        """Large JSON literal on a single line or multiple lines should not skew nesting."""
        code = (
            "if (a) {\n"
            "  const json = '[{\"a\": {\"b\": 1}}, {\"c\": 2}]';\n"
            "}"
        )
        _, _, nest = analyze(code, lang="js")
        self.assertEqual(nest, 1, "JSON strings should not skew nesting")


# ═══════════════════════════════════════════════════════════════════════════
#  CROSS-METRIC INTEGRATION TESTS
#  Verify all three metrics on the same code snippet at once.
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegration(unittest.TestCase):

    def test_simple_if(self):
        cc, cog, nest = analyze("if (a) {\n  x = 1;\n}")
        self.assertEqual(cc, 2)
        self.assertEqual(cog, 1)
        self.assertEqual(nest, 1)

    def test_if_else_with_and(self):
        """if(a && b) { } else { }
        CC:  if(+1) + &&(+1) = 2 decisions → CC=3
        Cog: if(+1) + &&seq(+1) + else(+1) = 3
        Nest: 1 (one brace level) """
        cc, cog, nest = analyze(
            "if (a && b) {\n  x=1;\n} else {\n  x=2;\n}")
        self.assertEqual(cc, 3)
        self.assertEqual(cog, 3)
        self.assertEqual(nest, 1)

    def test_nested_for_if_catch(self):
        """for { if { } catch { } }
        CC:  for(+1) + if(+1) + catch(+1) = 3 → CC=4
        Cog: for(+1,n=0) + if(+2,n=1) + catch(+2,n=1) = 5
        Nest: 3 (for > try > if/catch) """
        code = (
            "for (int i=0; i<n; i++) {\n"
            "  try {\n"
            "    if (a) {\n      x=1;\n    }\n"
            "  } catch (Exception e) {\n    y=2;\n  }\n}")
        cc, cog, nest = analyze(code)
        self.assertEqual(cc, 4)
        self.assertEqual(cog, 5)
        self.assertEqual(nest, 3)

    def test_switch_multiple_cases(self):
        """switch with 3 cases
        CC:  3 cases = 3 decisions → CC=4
        Cog: switch(+1) = 1 (cases not counted)
        Nest: 2 (switch block > case bodies share the block)"""
        cc, cog, nest = analyze(
            "switch (x) {\n  case 1: a=1; break;\n"
            "  case 2: a=2; break;\n  case 3: a=3; break;\n}")
        self.assertEqual(cc, 4)
        self.assertEqual(cog, 1)
        self.assertEqual(nest, 1)

    def test_complex_method(self):
        """Realistic C# method with multiple constructs.

        foreach (nest=0): CC+1, Cog: +1
          if (&&) (nest=1): CC+1+1, Cog: +2 (if) +1 (&&seq)
          else if (nest=1): CC+1, Cog: +1 (hybrid)
            for (nest=2): CC+1, Cog: +3 (for at nest=2, inside else-if brace)
        => Wait, let's trace it carefully below.
        """
        code = (
            "foreach (var item in list) {\n"
            "  if (item.IsValid && item.IsActive) {\n"
            "    Process(item);\n"
            "  } else if (item.NeedsRetry) {\n"
            "    for (int i=0; i<3; i++) {\n"
            "      Retry(item);\n"
            "    }\n"
            "  }\n}")
        cc, cog, nest = analyze(code, lang="cs")
        # CC: foreach(+1) + if(+1) + &&(+1) + else-if's if(+1) + for(+1) = 5 + 1 = 6
        self.assertEqual(cc, 6)
        # Cog trace:
        #   foreach at nest=0:     +1         → total=1
        #   if at nest=1:          +1+1 = +2  → total=3
        #   && seq:                +1         → total=4
        #   } else if (hybrid):   +1         → total=5
        #   for at nest=2:         +1+2 = +3  → total=8
        self.assertEqual(cog, 8)

    def test_jellyfish_example1_all_metrics(self):
        """Cross-validate Jellyfish example 1 on all metrics."""
        code = (
            'if (score >= 90) {\n  grade = "A";\n}\n'
            'else if (score >= 80) {\n  grade = "B";\n}\n'
            'else if (score >= 70) {\n  grade = "C";\n}\n'
            'else if (score >= 60) {\n  grade = "D";\n}\n'
            'else {\n  grade = "F";\n}')
        cc, cog, nest = analyze(code)
        self.assertEqual(cc, 5)
        # Cog: if(+1) + else-if(+1) + else-if(+1) + else-if(+1) + else(+1) = 5
        self.assertEqual(cog, 5)
        self.assertEqual(nest, 1)


# ═══════════════════════════════════════════════════════════════════════════
#  PYTHON INDENTATION ANALYZER + GO/RUST EXTRA PATTERNS
# ═══════════════════════════════════════════════════════════════════════════


class TestPythonIndentationMetrics(unittest.TestCase):
    """Regression tests for Python-only CC/cognitive fixes (ternary + and/or sequences)."""

    def test_conditional_expression_single_decision(self):
        """`x if cond else y` must count as one decision (not if + ternary)."""
        cc, cog, _ = analyze_py("x = a if cond else b\n")
        self.assertEqual(cc, 2, "base 1 + one ternary expression")
        self.assertEqual(cog, 0)

    def test_if_and_chain_cognitive_matches_sequence_rule(self):
        """if + one `and` sequence → cognitive 2 (structural + fundamental)."""
        cc, cog, _ = analyze_py("if a and b and c:\n    x = 1\n")
        self.assertEqual(cc, 4, "base + if + 2× and")
        self.assertEqual(cog, 2)

    def test_if_and_or_two_sequences(self):
        _, cog, _ = analyze_py("if a and b or c:\n    pass\n")
        self.assertEqual(cog, 3, "if + and-seq + or-seq")


class TestGoRustCyclomaticExtras(unittest.TestCase):
    """Go `for { }` and Rust `match` arms (=>) cyclomatic coverage."""

    def test_go_infinite_for_loop(self):
        cc, _, _ = analyze(
            "package main\nfunc f() {\n  for {\n    break\n  }\n}\n",
            lang="go",
        )
        self.assertEqual(cc, 2, "base 1 + for {")

    def test_rust_match_counts_each_arm(self):
        code = (
            "fn f(x: i32) {\n"
            "  match x {\n"
            "    1 => a(),\n"
            "    2 => b(),\n"
            "    _ => c(),\n"
            "  }\n"
            "}\n"
        )
        cc, _, _ = analyze(code, lang="rust")
        self.assertEqual(cc, 4, "base 1 + three => arms (like switch cases)")


# ═══════════════════════════════════════════════════════════════════════════
#  STRING / COMMENT CLEANING — line alignment and multi-line string literals
# ═══════════════════════════════════════════════════════════════════════════

class TestCleanerLineAlignment(unittest.TestCase):
    """The cleaned source must keep every line, or metrics shift / crash."""

    def assert_same_lines(self, code, lang):
        cleaned = _clean_cstyle_code(code, lang)
        self.assertEqual(len(cleaned), len(code))
        self.assertEqual(cleaned.count("\n"), code.count("\n"))
        return cleaned

    def test_java_text_block_line_continuation(self):
        # Regression: a trailing '\' in a text block swallowed the newline,
        # leaving the cleaned source one line short (IndexError in analysis).
        code = (
            "class A {\n"
            '    String s = """\n'
            "        first \\\n"
            "        second \\\n"
            '        """;\n'
            "    void f(int x) {\n"
            "        if (x > 0) { return; }\n"
            "    }\n"
            "}"
        )
        self.assert_same_lines(code, "java")
        cc, _, _ = analyze(code, lang="java")
        self.assertEqual(cc, 2)

    def test_java_text_block_with_quotes_hides_keywords(self):
        code = (
            "class B {\n"
            '    String s = """\n'
            '        He said "if (a) { while (b) {" and left\n'
            '        """;\n'
            "    void f(int x) {\n"
            "        if (x > 0) { return; }\n"
            "    }\n"
            "}"
        )
        cleaned = self.assert_same_lines(code, "java")
        self.assertNotIn("while", cleaned)
        cc, _, nest = analyze(code, lang="java")
        self.assertEqual(cc, 2, "only the real if counts")
        self.assertEqual(nest, 3, "class + method + if: braces inside the text block are ignored")

    def test_escaped_newline_in_js_string(self):
        code = "const s = 'a\\\nb';\nif (x) { y(); }\n"
        self.assert_same_lines(code, "js")
        cc, _, _ = analyze(code, lang="js")
        self.assertEqual(cc, 2)

    def test_csharp_verbatim_string_trailing_backslash(self):
        code = 'var p = @"C:\\temp\\";\nif (x) { y(); }\n'
        cleaned = self.assert_same_lines(code, "cs")
        self.assertIn("if (x)", cleaned, "string must close at the quote")

    def test_csharp_verbatim_doubled_quote(self):
        code = 'var s = @"say ""if (a)"" now";\nif (x) { y(); }\n'
        cc, _, _ = analyze(code, lang="cs")
        self.assertEqual(cc, 2)

    def test_csharp_raw_string_literal(self):
        code = 'var s = """\n  {"if (a)": 1}\n  """;\nif (x) { y(); }\n'
        self.assert_same_lines(code, "cs")
        cc, _, nest = analyze(code, lang="cs")
        self.assertEqual((cc, nest), (2, 1))

    def test_kotlin_raw_string(self):
        code = 'val s = """\n  if (a) { "x" }\n"""\nif (x) { y() }\n'
        cc, _, _ = analyze(code, lang="kotlin")
        self.assertEqual(cc, 2)

    def test_go_raw_string(self):
        code = 'q := `SELECT "if (a)"\nFROM t`\nif x > 0 {\n}\n'
        cleaned = self.assert_same_lines(code, "go")
        self.assertNotIn("SELECT", cleaned)

    def test_stray_quote_does_not_swallow_following_lines(self):
        # Rust lifetime: a single ' must not hide the code below it
        code = "struct S<'a> {\n  x: &str,\n}\nfn f(x: i32) {\n  if x > 0 { }\n}\n"
        cleaned = self.assert_same_lines(code, "rust")
        self.assertIn("if x > 0", cleaned)

    def test_js_template_expression_is_code(self):
        code = "const s = `a ${ok ? 'y' : 'n'} b { if (z) }`;\n"
        cleaned = self.assert_same_lines(code, "js")
        self.assertIn("ok ?", cleaned)
        self.assertNotIn("if (z)", cleaned)
        cc, _, nest = analyze(code, lang="js")
        self.assertEqual((cc, nest), (2, 0), "ternary inside ${} counts; template braces do not")

    def test_js_nested_template_literals(self):
        code = "const s = `x ${c ? `<p>${d}</p>` : ''} y`;\nif (q) { w(); }\n"
        cleaned = self.assert_same_lines(code, "js")
        self.assertNotIn("<p>", cleaned)
        self.assertIn("if (q)", cleaned)


# ═══════════════════════════════════════════════════════════════════════════
#  FUNCTION DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def count_functions(code: str, lang: str):
    fm = FileMetrics("__test__", lang)
    return _analyze_cstyle(code, fm).functions


class TestFunctionDetection(unittest.TestCase):

    def test_js_control_flow_is_not_a_function(self):
        code = (
            "function f(id) {\n"
            "  if (id > 0) {\n"
            "  } else if (id < 0) {\n"
            "  }\n"
            "  for (const x of xs) {\n"
            "  }\n"
            "  try { a(); } catch (e) {\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(count_functions(code, "js"), 1)
        self.assertEqual([n for n, _, _ in _find_function_boundaries(code, "js")], ["f"])

    def test_js_method_and_arrow_still_counted(self):
        code = "class A {\n  load(id) {\n  }\n}\nconst g = (x) => x;\n"
        self.assertEqual(count_functions(code, "js"), 2)

    def test_java_package_private_method(self):
        code = "class T {\n  void shouldWork() {\n  }\n  static int helper(int a) {\n  }\n}\n"
        self.assertEqual(count_functions(code, "java"), 2)

    def test_java_statements_are_not_functions(self):
        code = (
            "class T {\n"
            "  public void f() {\n"
            "    return compute(a,\n"
            "        b);\n"
            "    String s = format(x);\n"
            "    Runnable r = new Runnable() {\n"
            "    };\n"
            "    } else if (x) {\n"
            "  }\n"
            "  abstract void g();\n"
            "}\n"
        )
        self.assertEqual(count_functions(code, "java"), 1)

    def test_c_prototype_is_not_a_definition(self):
        code = "int add(int a, int b);\nint add(int a, int b) {\n  return a + b;\n}\n"
        self.assertEqual(count_functions(code, "c"), 1)

    def test_objc_methods(self):
        code = (
            "@implementation Foo\n"
            "- (void)load:(int)x {\n"
            "  if (x) { }\n"
            "}\n"
            "+ (instancetype)shared {\n"
            "}\n"
            "@end\n"
        )
        self.assertEqual(count_functions(code, "objc"), 2)
        self.assertEqual([n for n, _, _ in _find_function_boundaries(code, "objc")], ["load", "shared"])

    def test_groovy_def_counted_dsl_blocks_not(self):
        code = (
            "def build(String target) {\n"
            "}\n"
            "pipeline {\n"
            "  stages {\n"
            "    stage('Build') {\n"
            "      steps { echo 'hi' }\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(count_functions(code, "groovy"), 1)

    def test_braces_in_strings_do_not_break_boundaries(self):
        code = "function f() {\n  const s = '}';\n  if (a) { b(); }\n}\nfunction g() {\n}\n"
        self.assertEqual(
            [(n, s, e) for n, s, e in _find_function_boundaries(code, "js")],
            [("f", 0, 3), ("g", 4, 5)],
        )


# ═══════════════════════════════════════════════════════════════════════════
#  VUE / SVELTE AND NEW FILE TYPES
# ═══════════════════════════════════════════════════════════════════════════

VUE_SAMPLE = """<template>
  <div class="wrapper">
    <ul v-if="items.length && !loading">
      <li v-for="item in items" :key="item.id">{{ item.ok ? 'yes' : 'no' }}</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
function load(id: number) {
  if (id > 0) {
    console.log('loading', id)
  }
}
</script>

<style scoped>
@media (max-width: 600px) {
  .wrapper { padding: 0; }
}
</style>
"""


class TestSingleFileComponents(unittest.TestCase):

    def test_extract_keeps_only_script_and_line_numbers(self):
        out = _extract_sfc_script(VUE_SAMPLE)
        self.assertEqual(out.count("\n"), VUE_SAMPLE.count("\n"))
        self.assertNotIn("v-if", out)
        self.assertNotIn("@media", out)
        self.assertEqual(out.split("\n")[9], "function load(id: number) {")

    def test_multiple_script_blocks_and_src(self):
        sfc = (
            '<script src="./a.ts"></script>\n'
            "<script>\nexport default { name: 'A' }\n</script>\n"
            '<script setup lang="ts">\nconst x = 1\n</script>\n'
        )
        out = _extract_sfc_script(sfc)
        self.assertIn("export default", out)
        self.assertIn("const x = 1", out)
        self.assertEqual(out.count("\n"), sfc.count("\n"))

    def _write(self, tmp, name, text):
        import os
        path = os.path.join(tmp, name)
        with open(path, "w") as f:
            f.write(text)
        return path

    def test_vue_file_metrics_ignore_template_and_style(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fm = analyze_file(self._write(tmp, "Sample.vue", VUE_SAMPLE), "Sample.vue")
        self.assertEqual(fm.lang, "vue")
        self.assertEqual(fm.total_lines, VUE_SAMPLE.count("\n") + 1)
        self.assertEqual(fm.code_lines, 5, "script code lines only")
        self.assertEqual((fm.cyclomatic, fm.functions), (2, 1))
        self.assertEqual([(f.name, f.start_line) for f in fm.function_metrics], [("load", 10)])

    def test_svelte_file(self):
        import tempfile
        src = "<script>\n  let n = 0;\n  function inc() { if (n < 5) n++; }\n</script>\n{#if n > 2}<p>{n}</p>{/if}\n"
        with tempfile.TemporaryDirectory() as tmp:
            fm = analyze_file(self._write(tmp, "C.svelte", src), "C.svelte")
        self.assertEqual((fm.lang, fm.cyclomatic, fm.functions), ("svelte", 2, 1))

    def test_detect_lang_new_types(self):
        cases = {
            "a.mts": "js", "a.cts": "js", "A.vue": "vue", "A.svelte": "svelte",
            "a.m": "objc", "a.mm": "objc", "a.groovy": "groovy",
            "build.gradle": "groovy", "Jenkinsfile": "groovy",
        }
        for path, lang in cases.items():
            self.assertEqual(_detect_lang(path), lang, path)

    def test_matlab_m_file_is_skipped(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            matlab = self._write(tmp, "calc.m", "function y = calc(x)\n  % comment\n  y = x * 2;\nend\n")
            objc = self._write(tmp, "Foo.m", '#import "Foo.h"\n@implementation Foo\n@end\n')
            self.assertIsNone(analyze_file(matlab, "calc.m"))
            self.assertEqual(analyze_file(objc, "Foo.m").lang, "objc")

    def test_scan_project_finds_new_types(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "Sample.vue", VUE_SAMPLE)
            self._write(tmp, "Jenkinsfile", "pipeline {\n  agent any\n}\n")
            self._write(tmp, "build.gradle", "plugins { id 'java' }\n")
            self._write(tmp, "util.mts", "export const a = 1;\n")
            self._write(tmp, "calc.m", "x = 1;\n")  # MATLAB: skipped
            paths = sorted(m.path for m in scan_project(tmp))
        self.assertEqual(paths, ["Jenkinsfile", "Sample.vue", "build.gradle", "util.mts"])

    def test_logging_scans_vue_script_only(self):
        import tempfile
        import logging_analysis as la
        sfc = VUE_SAMPLE.replace("</template>", "  <!-- console.log('not code') -->\n</template>")
        with tempfile.TemporaryDirectory() as tmp:
            fm = la.analyze_file(self._write(tmp, "Sample.vue", sfc), "Sample.vue")
        self.assertEqual((fm.lang, fm.active_log_lines), ("vue", 1))
        self.assertEqual(fm.log_line_details[0][0], 13, "reported at its real line number")


# ═══════════════════════════════════════════════════════════════════════════
#  FIXES VERIFIED AGAINST ROSLYN (C# compiler syntax tree)
#  See tools/roslyn_check/ for the reference implementation and comparison.
# ═══════════════════════════════════════════════════════════════════════════

def metrics(code: str, lang: str = "cs"):
    """(cyclomatic, cognitive) of a snippet analyzed as a file."""
    fm = _analyze_cstyle(code, FileMetrics("__test__", lang))
    return fm.cyclomatic, fm.cognitive


def functions(code: str, lang: str = "cs"):
    """[(name, 1-based start line, cyclomatic, cognitive), ...]"""
    return [(f.name, f.start_line, f.cyclomatic, f.cognitive)
            for f in _analyze_functions(code, "__test__", lang)]


class TestTernaryDetection(unittest.TestCase):

    def test_member_access_in_branches(self):
        self.assertEqual(metrics("var x = a != null ? a.Name : b.Name;")[0], 2)

    def test_multi_line_ternary(self):
        self.assertEqual(metrics("var x = cond\n    ? a.B\n    : c.D;")[0], 2)

    def test_nullable_types_are_not_ternaries(self):
        code = "class C {\n  public C(string? name) : base(name) {\n  }\n  int? Foo(Action<int, DateTime?> a) { return null; }\n}"
        self.assertEqual(metrics(code)[0], 1)

    def test_typescript_optional_members_are_not_ternaries(self):
        self.assertEqual(metrics("interface P {\n  name?: string;\n  age?: number;\n}", "js")[0], 1)

    def test_java_wildcard_is_not_ternary(self):
        self.assertEqual(metrics("for (Class<?> k : klasses) {\n}", "java")[0], 2)

    def test_null_conditional_and_coalescing_are_not_ternaries(self):
        self.assertEqual(metrics("var n = a?.b ?? c;")[0], 2, "only ?? counts")

    def test_nested_multi_line_ternary_nests(self):
        code = "int F() {\n  return a\n    ? b\n      ? 1\n      : 2\n    : 3;\n}"
        self.assertEqual(metrics(code)[1], 3, "outer +1, inner +2")


class TestCatchDetection(unittest.TestCase):

    def test_bare_catch_counts(self):
        self.assertEqual(metrics("try {\n  a();\n}\ncatch\n{\n}")[0], 2)

    def test_promise_catch_call_does_not_count(self):
        self.assertEqual(metrics("fetch(u).then(r => r.json()).catch(e => log(e));", "js")[0], 1)


class TestParenlessConditions(unittest.TestCase):

    def test_go(self):
        code = "func f(x int) {\n  if x > 0 {\n  } else if x < 0 {\n  }\n  for i := range xs {\n  }\n}"
        cc, cog = metrics(code, "go")
        self.assertEqual(cc, 4, "if, else if, for")
        self.assertEqual(cog, 3, "if +1, else if +1, for +1")

    def test_rust(self):
        code = "fn f(x: i32) {\n  if x > 0 {\n  }\n  while let Some(v) = it.next() {\n  }\n}"
        self.assertEqual(metrics(code, "rust")[0], 3)

    def test_swift_guard_else_is_not_a_branch(self):
        code = "func f(x: Int?) {\n  guard let v = x else {\n    return\n  }\n  if v > 0 {\n  }\n}"
        cc, cog = metrics(code, "swift")
        self.assertEqual(cc, 3, "guard, if")
        self.assertEqual(cog, 2, "guard +1, if +1; the guard's else adds nothing")


class TestCognitiveNestingRoles(unittest.TestCase):
    """Only control-flow braces (and nested lambdas/functions) nest."""

    def test_method_body_does_not_nest(self):
        code = "class C {\n  public void F() {\n    if (a) {\n      x();\n    }\n  }\n}"
        self.assertEqual(metrics(code)[1], 1)
        self.assertEqual(functions(code)[0][3], 1)

    def test_allman_braces(self):
        code = ("namespace N\n{\n  class C\n  {\n    void F()\n    {\n      for (;;)\n      {\n"
                "        if (a)\n        {\n        }\n      }\n    }\n  }\n}")
        self.assertEqual(metrics(code)[1], 3, "for +1, if +2")

    def test_using_lock_try_and_initializers_do_not_nest(self):
        code = ("void F() {\n  using (var s = Open()) {\n    lock (o) {\n      try {\n"
                "        var p = new P {\n          A = b ? 1 : 2\n        };\n      }\n"
                "      finally {\n      }\n    }\n  }\n}")
        self.assertEqual(metrics(code)[1], 1, "ternary at nesting 0")

    def test_lambda_inside_method_nests(self):
        code = "void F() {\n  items.ForEach(x => {\n    if (x) {\n    }\n  });\n}"
        self.assertEqual(metrics(code)[1], 2)

    def test_expression_lambda_nests(self):
        self.assertEqual(metrics("void F() {\n  var q = xs.Select(x => x.A ? 1 : 2);\n}")[1], 2)

    def test_case_then_if_on_allman_brace(self):
        code = ("void F() {\n  switch (k) {\n    case 1:\n      if (a)\n      {\n"
                "        for (;;) { }\n      }\n      break;\n  }\n}")
        self.assertEqual(metrics(code)[1], 6, "switch +1, if +2, for +3")

    def test_property_pattern_on_if_line(self):
        code = "void F() {\n  if (o is { A: 1 })\n  {\n    if (b)\n    {\n    }\n  }\n}"
        self.assertEqual(metrics(code)[1], 3, "if +1, nested if +2")


class TestBracelessBodies(unittest.TestCase):

    def test_for_then_if_without_braces(self):
        code = "void F() {\n  for (int k = 0; k < n; k++)\n    if (a[k])\n    {\n      b();\n    }\n  if (c) { }\n}"
        self.assertEqual(metrics(code)[1], 4, "for +1, nested if +2, later if +1")

    def test_else_newline_if_is_else_if(self):
        code = "void F() {\n  if (a)\n    x();\n  else\n    if (b)\n      y();\n}"
        self.assertEqual(metrics(code)[1], 2, "if +1, else-if +1")


class TestMultiLineLogicalSequences(unittest.TestCase):

    def test_sequence_continues_over_lines(self):
        code = "bool F() {\n  return a\n    || b\n    || c\n    || d;\n}"
        self.assertEqual(metrics(code)[1], 1)

    def test_separate_lambdas_are_separate_sequences(self):
        code = "var q = xs\n  .Where(x => x.A || x.B)\n  .Where(x => x.C || x.D);"
        self.assertEqual(metrics(code)[1], 2)


class TestCSharpSwitchAndWhen(unittest.TestCase):

    def test_switch_expression(self):
        code = ("decimal D(Order o) {\n  return o.Status switch\n  {\n    S.New => 0m,\n"
                "    S.Paid when o.Amount > 1000 => 0.1m,\n    _ when o.Vip => 0.2m,\n    _ => 0.05m,\n  };\n}")
        cc, cog = metrics(code)
        self.assertEqual(cc, 1 + 2 + 2, "2 non-discard arms + 2 guards")
        self.assertEqual(cog, 1)

    def test_guard_on_line_above_arrow(self):
        code = "var m = a switch\n{\n  Cat c when c.Legs == 4\n    => 1,\n  _\n    => 2,\n};"
        self.assertEqual(metrics(code)[0], 3, "1 arm + 1 guard")

    def test_case_guard_and_catch_filter(self):
        code = ("switch (x) {\n  case int i when i > 0:\n    break;\n}\n"
                "try { } catch (E e) when (e.Code == 1) { }")
        self.assertEqual(metrics(code)[0], 1 + 2 + 2, "case + guard, catch + filter")

    def test_when_as_identifier_does_not_count(self):
        code = "void F(DateTime when) {\n  T(when: when);\n  if (when < now) { }\n}"
        self.assertEqual(metrics(code)[0], 2)

    def test_goto_case_does_not_count(self):
        code = "switch (x) {\n  case 1:\n    break;\n  case 2:\n    goto case 1;\n}"
        self.assertEqual(metrics(code)[0], 3)

    def test_interpolation_holes_are_code(self):
        self.assertEqual(metrics('var s = $"{(a ? "x" : "y")} {{literal ? }}";')[0], 2)


class TestCSharpFunctionDetection(unittest.TestCase):

    def names(self, code):
        return [f[0] for f in functions(code)]

    def test_methods_without_modifier_generic_and_destructor(self):
        code = ("class C\n{\n  void Reset()\n  {\n  }\n  public T First<T>(IEnumerable<T> xs) where T : class\n  {\n"
                "    return default;\n  }\n  ~C()\n  {\n  }\n  public static C operator +(C a, C b)\n  {\n    return a;\n  }\n}")
        self.assertEqual(self.names(code), ["Reset", "First", "C", "operator+"])

    def test_expression_bodied_member_does_not_take_next_body(self):
        code = ("class C\n{\n  public int A() =>\n    1;\n  protected override void B(X x)\n"
                "    => x.Do();\n  public int Next()\n  {\n    if (a) { }\n    return 1;\n  }\n}")
        self.assertEqual(functions(code), [("Next", 7, 2, 1)])

    def test_primary_constructor_is_not_a_function(self):
        code = "public class Ex(string id) : Exception($\"{id}\")\n{\n}\npublic record R(int A) { }"
        self.assertEqual(functions(code), [])

    def test_accessors_with_block_bodies(self):
        code = ("class C\n{\n  public int Count\n  {\n    get { return _c > 0 ? _c : 0; }\n    private set\n"
                "    {\n      if (value < 0) throw new X();\n      _c = value;\n    }\n  }\n  public int Auto { get; set; }\n}")
        self.assertEqual(functions(code), [("Count.get", 5, 2, 1), ("Count.set", 6, 2, 1)])

    def test_statements_are_not_functions(self):
        code = ("class C\n{\n  public async Task F()\n  {\n    await Task.WhenAll(a,\n      b);\n"
                "    return Compute(a,\n      b);\n  }\n}")
        self.assertEqual(self.names(code), ["F"])


class TestJsArrowFunctions(unittest.TestCase):

    def test_expression_bodied_arrow_ends_with_its_statement(self):
        code = ("const half = (x: number) =>\n  x > 0\n    ? x / 2\n    : 0;\n"
                "function next() {\n  if (a) { b(); }\n}")
        self.assertEqual(
            [(n, s, e) for n, s, e in _find_function_boundaries(code, "js")],
            [("half", 0, 3), ("next", 4, 6)],
        )


class TestCSharpRoslynFixture(unittest.TestCase):
    """test_fixtures/csharp/OrderService.cs against values computed by Roslyn
    (tools/roslyn_check/Oracle.cs, expected values in OrderService.expected.json)."""

    def test_matches_roslyn(self):
        import json
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        src = os.path.join(here, "test_fixtures", "csharp", "OrderService.cs")
        with open(os.path.join(here, "test_fixtures", "csharp", "OrderService.expected.json")) as f:
            expected = json.load(f)
        fm = analyze_file(src, "OrderService.cs")
        self.assertEqual(fm.cyclomatic, expected["file_cyclomatic"])
        got = {f.start_line: (f.cyclomatic, f.cognitive) for f in fm.function_metrics}
        for e in expected["functions"]:
            with self.subTest(function=e["name"], line=e["line"]):
                self.assertIn(e["line"], got, "function not detected")
                self.assertEqual(got[e["line"]], (e["cyclomatic"], e["cognitive"]))
        self.assertEqual(len(got), len(expected["functions"]), "no extra functions")


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main()
