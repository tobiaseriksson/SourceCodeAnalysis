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

  Expected output (all tests passing):
    Ran 83 tests in 0.002s
    OK
"""

import sys
import unittest
from complexity_analysis import (
    FileMetrics,
    _analyze_cstyle,
    _count_logical_operator_sequences,
)


# ─── Helper ─────────────────────────────────────────────────────────────────

def analyze(code: str, lang: str = "cs"):
    """Analyze a code snippet and return (cyclomatic, cognitive, max_nesting)."""
    fm = FileMetrics("__test__", lang)
    fm = _analyze_cstyle(code, fm)
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


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main()
