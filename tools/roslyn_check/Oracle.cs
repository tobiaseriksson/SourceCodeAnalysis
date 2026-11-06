#:package Microsoft.CodeAnalysis.CSharp@4.12.0
#:property JsonSerializerIsReflectionEnabledByDefault=true
#:property PublishAot=false
// Reference ("oracle") metrics for C# files, computed from the Roslyn syntax tree.
//
// Implements the SAME definitions complexity_analysis.py documents:
//   Cyclomatic = 1 + if, while, do-while, for, foreach, case labels, catch,
//                `when` (catch filters, case and switch-arm guards),
//                non-discard switch-expression arms, ?:, ??, each && and ||
//   Cognitive  = SonarSource 2023 (structural +1+nesting, else/else-if +1,
//                logical-operator sequences, lambdas/local functions nest)
// Constructs outside that CC definition are counted separately ("extra_*")
// so definition gaps can be told apart from implementation bugs.
//
// Usage: dotnet run tools/roslyn_check/Oracle.cs -- <root> [<root> ...]   → JSON on stdout
// Requires the .NET 10 SDK (file-based apps); fetches Microsoft.CodeAnalysis.CSharp from NuGet.
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

var skip = new HashSet<string> { "bin", "obj", "node_modules", ".git", "packages" };
var files = new List<(string root, string path)>();
foreach (var root in args)
{
    if (File.Exists(root)) { files.Add((Path.GetDirectoryName(root)!, root)); continue; }
    foreach (var f in Directory.EnumerateFiles(root, "*.cs", SearchOption.AllDirectories))
    {
        var rel = Path.GetRelativePath(root, f);
        if (rel.Split(Path.DirectorySeparatorChar).Any(skip.Contains)) continue;
        var name = Path.GetFileName(f);
        if (name.EndsWith(".Designer.cs") || name.EndsWith(".g.cs") || name.EndsWith(".g.i.cs")) continue;
        files.Add((root, f));
    }
}

var output = new List<object>();
foreach (var (root, path) in files)
{
    var text = File.ReadAllText(path);
    var tree = CSharpSyntaxTree.ParseText(text, new CSharpParseOptions(LanguageVersion.Preview));
    var rootNode = tree.GetRoot();
    int Line(int pos) => tree.GetLineSpan(new Microsoft.CodeAnalysis.Text.TextSpan(pos, 0)).StartLinePosition.Line + 1;

    var members = new List<object>();
    foreach (var node in rootNode.DescendantNodes())
    {
        string? kind = null, name = null;
        SyntaxNode? body = null; bool exprBody = false;
        switch (node)
        {
            case MethodDeclarationSyntax m: kind = "method"; name = m.Identifier.Text; body = m.Body; exprBody = m.ExpressionBody != null; break;
            case ConstructorDeclarationSyntax c: kind = "ctor"; name = c.Identifier.Text; body = c.Body; exprBody = c.ExpressionBody != null; break;
            case DestructorDeclarationSyntax d: kind = "dtor"; name = d.Identifier.Text; body = d.Body; exprBody = d.ExpressionBody != null; break;
            case OperatorDeclarationSyntax o: kind = "operator"; name = "operator" + o.OperatorToken.Text; body = o.Body; exprBody = o.ExpressionBody != null; break;
            case ConversionOperatorDeclarationSyntax co: kind = "operator"; name = "operator " + co.Type; body = co.Body; exprBody = co.ExpressionBody != null; break;
            case AccessorDeclarationSyntax a:
                kind = "accessor";
                var owner = a.Parent?.Parent switch { PropertyDeclarationSyntax p => p.Identifier.Text, EventDeclarationSyntax e => e.Identifier.Text, IndexerDeclarationSyntax => "this[]", _ => "?" };
                name = owner + "." + a.Keyword.Text; body = a.Body; exprBody = a.ExpressionBody != null; break;
            case LocalFunctionStatementSyntax lf: kind = "local"; name = lf.Identifier.Text; body = lf.Body; exprBody = lf.ExpressionBody != null; break;
        }
        if (kind == null) continue;
        // Declaration line = first token that is not part of an attribute list
        var first = node.DescendantTokens().First(t => !t.Parent!.AncestorsAndSelf().Any(x => x is AttributeListSyntax && x.Parent == node));
        members.Add(new
        {
            kind, name,
            top_level = node.Parent is GlobalStatementSyntax,
            decl_line = Line(first.SpanStart),
            end_line = Line(node.Span.End),
            body = body != null ? "block" : exprBody ? "expr" : "none",
            cc = 1 + Metrics.Cc(node),
            cog = Metrics.Cog(node),
            extra = Metrics.Extra(node),
        });
    }
    output.Add(new
    {
        path = Path.GetRelativePath(root, path),
        parse_errors = tree.GetDiagnostics().Count(d => d.Severity == DiagnosticSeverity.Error),
        cc = 1 + Metrics.Cc(rootNode),
        cc_lines = Metrics.CcLines(rootNode, Line),
        extra = Metrics.Extra(rootNode),
        members,
    });
}
Console.WriteLine(JsonSerializer.Serialize(output, new JsonSerializerOptions { WriteIndented = false }));

static class Metrics
{
    public static int Cc(SyntaxNode n) => n.DescendantNodesAndSelf().Count(x => x switch
    {
        IfStatementSyntax or WhileStatementSyntax or DoStatementSyntax or ForStatementSyntax
            or ForEachStatementSyntax or ForEachVariableStatementSyntax
            or CaseSwitchLabelSyntax or CasePatternSwitchLabelSyntax
            or CatchClauseSyntax or CatchFilterClauseSyntax or ConditionalExpressionSyntax
            or WhenClauseSyntax => true,
        SwitchExpressionArmSyntax arm => arm.Pattern is not DiscardPatternSyntax,
        BinaryExpressionSyntax b => b.IsKind(SyntaxKind.CoalesceExpression) || b.IsKind(SyntaxKind.LogicalAndExpression) || b.IsKind(SyntaxKind.LogicalOrExpression),
        _ => false,
    });

    // Line of the token that represents each decision point
    public static Dictionary<int, int> CcLines(SyntaxNode n, Func<int, int> line)
    {
        var d = new Dictionary<int, int>();
        foreach (var x in n.DescendantNodesAndSelf())
        {
            SyntaxToken? t = x switch
            {
                IfStatementSyntax s => s.IfKeyword,
                WhileStatementSyntax s => s.WhileKeyword,
                DoStatementSyntax s => s.WhileKeyword,
                ForStatementSyntax s => s.ForKeyword,
                ForEachStatementSyntax s => s.ForEachKeyword,
                ForEachVariableStatementSyntax s => s.ForEachKeyword,
                CaseSwitchLabelSyntax s => s.Keyword,
                CasePatternSwitchLabelSyntax s => s.Keyword,
                CatchClauseSyntax s => s.CatchKeyword,
                CatchFilterClauseSyntax s => s.WhenKeyword,
                WhenClauseSyntax s => s.WhenKeyword,
                SwitchExpressionArmSyntax s when s.Pattern is not DiscardPatternSyntax => s.EqualsGreaterThanToken,
                ConditionalExpressionSyntax s => s.QuestionToken,
                BinaryExpressionSyntax b when b.IsKind(SyntaxKind.CoalesceExpression) || b.IsKind(SyntaxKind.LogicalAndExpression) || b.IsKind(SyntaxKind.LogicalOrExpression) => b.OperatorToken,
                _ => null,
            };
            if (t is SyntaxToken tok) { var l = line(tok.SpanStart); d[l] = d.GetValueOrDefault(l) + 1; }
        }
        return d;
    }

    // Decision points NOT in the script's CC definition
    public static Dictionary<string, int> Extra(SyntaxNode n)
    {
        var d = n.DescendantNodesAndSelf().ToList();
        return new()
        {
            ["switch_expr_arms"] = d.OfType<SwitchExpressionArmSyntax>().Count(a => a.Pattern is not DiscardPatternSyntax),
            ["case_when_guards"] = d.OfType<WhenClauseSyntax>().Count(),
            ["pattern_and_or"] = d.OfType<BinaryPatternSyntax>().Count(),
            ["null_cond_access"] = d.OfType<ConditionalAccessExpressionSyntax>().Count(),
            ["coalesce_assign"] = d.Count(x => x.IsKind(SyntaxKind.CoalesceAssignmentExpression)),
            ["interp_ternary"] = d.OfType<InterpolationSyntax>().Sum(i => i.DescendantNodes().Count(x => x is ConditionalExpressionSyntax)),
        };
    }

    public static int Cog(SyntaxNode n) { int c = 0; Walk(n, 0, ref c, true); return c; }

    static bool IsLogical(SyntaxNode n) => n.IsKind(SyntaxKind.LogicalAndExpression) || n.IsKind(SyntaxKind.LogicalOrExpression);

    static void Walk(SyntaxNode n, int nest, ref int c, bool isRoot = false)
    {
        switch (n)
        {
            case IfStatementSyntax s:
                c += s.Parent is ElseClauseSyntax ? 1 : 1 + nest;
                Walk(s.Condition, nest, ref c);
                Walk(s.Statement, nest + 1, ref c);
                if (s.Else != null)
                {
                    if (s.Else.Statement is IfStatementSyntax) Walk(s.Else.Statement, nest, ref c);
                    else { c += 1; Walk(s.Else.Statement, nest + 1, ref c); }
                }
                return;
            case SwitchStatementSyntax sw:
                c += 1 + nest;
                Walk(sw.Expression, nest, ref c);
                foreach (var sec in sw.Sections) Walk(sec, nest + 1, ref c);
                return;
            case SwitchExpressionSyntax se:
                c += 1 + nest;
                Walk(se.GoverningExpression, nest, ref c);
                foreach (var arm in se.Arms) Walk(arm, nest + 1, ref c);
                return;
            case ForStatementSyntax or ForEachStatementSyntax or ForEachVariableStatementSyntax or WhileStatementSyntax or DoStatementSyntax:
                c += 1 + nest;
                foreach (var ch in n.ChildNodes())
                    Walk(ch, ch is StatementSyntax ? nest + 1 : nest, ref c);
                return;
            case CatchClauseSyntax cc:
                c += 1 + nest;
                foreach (var ch in cc.ChildNodes()) Walk(ch, ch is BlockSyntax ? nest + 1 : nest, ref c);
                return;
            case ConditionalExpressionSyntax ce:
                c += 1 + nest;
                Walk(ce.Condition, nest, ref c);
                Walk(ce.WhenTrue, nest + 1, ref c);
                Walk(ce.WhenFalse, nest + 1, ref c);
                return;
            case GotoStatementSyntax:
                c += 1;
                break;
            case LambdaExpressionSyntax or AnonymousMethodExpressionSyntax:
                foreach (var ch in n.ChildNodes()) Walk(ch, nest + 1, ref c);
                return;
            case LocalFunctionStatementSyntax when !isRoot:
                foreach (var ch in n.ChildNodes()) Walk(ch, nest + 1, ref c);
                return;
            case BinaryExpressionSyntax b when IsLogical(b):
                var parent = b.Parent;
                while (parent is ParenthesizedExpressionSyntax) parent = parent.Parent;
                if (parent == null || !IsLogical(parent))
                {
                    // Root of a logical expression: +1 per run of like operators, in source order
                    var ops = new List<SyntaxKind>();
                    Collect(b, ops);
                    for (int i = 0; i < ops.Count; i++) if (i == 0 || ops[i] != ops[i - 1]) c += 1;
                }
                break;
        }
        foreach (var ch in n.ChildNodes()) Walk(ch, nest, ref c);
    }

    static void Collect(SyntaxNode n, List<SyntaxKind> ops)
    {
        while (n is ParenthesizedExpressionSyntax p) n = p.Expression;
        if (n is BinaryExpressionSyntax b && IsLogical(b))
        {
            Collect(b.Left, ops);
            ops.Add(b.Kind());
            Collect(b.Right, ops);
        }
    }
}
