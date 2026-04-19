
# Sample output from the complexity_analysis.py command


``` 
python ../SourceCodeAnalysis/complexity_analysis.py 

  Scanning: /Users/tobiaseriksson/Softhouse/CommonLantlivUtils
  Extensions: .c, .cc, .cjs, .cpp, .cs, .cshtml, .cxx, .dart, .go, .h, .hpp, .htm, .html, .hxx, .java, .js, .jsx, .kt, .kts, .mjs, .php, .py, .r, .razor, .rb, .rs, .sc, .scala, .swift, .ts, .tsx

==============================================================
  CODE COMPLEXITY ANALYSIS
==============================================================

FILES
  Total files analyzed:  83
    UI components:       0
    Business logic:      68
    Config / setup:      0
    Tests:               15
    Type definitions:    0
    Markup (HTML):       0

SIZE
  Total lines:           6,330
  Code lines:            4,858
  Comment lines:         550
  Blank lines:           922
  Comment ratio:         11.3%
  Avg code lines/file:   59
  Total functions:       236  (excl. HTML/markup)
  Avg functions/file:    2.8  (non-markup files only)

CYCLOMATIC COMPLEXITY  (excl. HTML/markup)
  Total:                 350
  Average / file:        4.2
  Median / file:         1
    Low     (1–10):        75 files  (90%)
    Moderate(11–20):      5 files  (6%)
    High    (21–50):     2 files  (2%)
    V. High (51–100):   1 files  (1%)
    Extreme (>100):     0 files  (0%)

COGNITIVE COMPLEXITY  (excl. HTML/markup)
  Total:                 604
  Average / file:        7.3
  Median / file:         0
    Low     (0–15):        68 files  (82%)
    Moderate(16–25):      7 files  (8%)
    High    (26–50):     7 files  (8%)
    V. High (51–100):   0 files  (0%)
    Extreme (>100):     1 files  (1%)

NESTING (max block/brace depth per file, excl. HTML/markup)
  Max depth (project):   12
  Median / file:         2
    Low     (0–2):        48 files  (58%)
    Moderate(3–4):     26 files  (31%)
    High    (5–6):     6 files  (7%)
    V. High (7–9):   2 files  (2%)
    Extreme (>9):     1 files  (1%)
  Files with depth ≥ 4:  16  (common style / ESLint max-depth default)

FUNCTIONS (count per file, excl. HTML/markup)
  Total (project):       236
  Average / file:        2.8
  Median / file:         1
    Low     (0–10):        75 files  (90%)
    Moderate(11–25):      7 files  (8%)
    High    (26–50):     1 files  (1%)
    V. High (51–100):   0 files  (0%)
    Extreme (>100):     0 files  (0%)

BUSINESS LOGIC ONLY
  Files:                 68
  Code lines:            3,545
  Avg CC / file:         4.6
  Avg Cognitive / file:  8.1

TOP 10 — HIGHEST CYCLOMATIC COMPLEXITY
  CC=  61  Cog=  132  Nest= 7  Fns= 13  Lines=  355  src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java
  CC=  21  Cog=   38  Nest= 4  Fns= 11  Lines=  110  src/main/java/com/tsoft/lantliv/common/Utils.java
  CC=  21  Cog=   25  Nest= 4  Fns=  5  Lines=  198  src/main/java/com/tsoft/lantliv/prestashop/old/Item.java
  CC=  14  Cog=   34  Nest= 5  Fns=  5  Lines=  165  src/main/java/com/tsoft/lantliv/common/PostgreSQLHelper.java
  CC=  14  Cog=   21  Nest= 3  Fns=  5  Lines=   67  src/main/java/com/tsoft/lantliv/common/FileUtils.java
  CC=  13  Cog=   31  Nest= 6  Fns=  2  Lines=   85  src/main/java/com/tsoft/lantliv/tools/ActivateOrDeactivateProductsInLantliv.java
  CC=  13  Cog=   19  Nest= 4  Fns= 11  Lines=  109  src/main/java/com/tsoft/lantliv/prestashop/xml/api/CategoryHelper.java
  CC=  11  Cog=   20  Nest= 5  Fns=  4  Lines=   73  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopCategoryApi.java
  CC=  10  Cog=   33  Nest= 8  Fns=  1  Lines=   78  src/main/java/com/tsoft/lantliv/tools/UpdateAllSupplierIDsInLantliv.java
  CC=  10  Cog=   18  Nest= 3  Fns=  6  Lines=  121  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopProductApi.java

TOP 10 — HIGHEST COGNITIVE COMPLEXITY
  CC=  61  Cog=  132  Nest= 7  Fns= 13  Lines=  355  src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java
  CC=  10  Cog=   39  Nest= 6  Fns=  3  Lines=   92  src/main/java/com/tsoft/lantliv/prestashop/json/api/PricewatchHttpClient.java
  CC=  21  Cog=   38  Nest= 4  Fns= 11  Lines=  110  src/main/java/com/tsoft/lantliv/common/Utils.java
  CC=  14  Cog=   34  Nest= 5  Fns=  5  Lines=  165  src/main/java/com/tsoft/lantliv/common/PostgreSQLHelper.java
  CC=  10  Cog=   33  Nest= 8  Fns=  1  Lines=   78  src/main/java/com/tsoft/lantliv/tools/UpdateAllSupplierIDsInLantliv.java
  CC=  13  Cog=   31  Nest= 6  Fns=  2  Lines=   85  src/main/java/com/tsoft/lantliv/tools/ActivateOrDeactivateProductsInLantliv.java
  CC=   8  Cog=   27  Nest= 5  Fns=  6  Lines=   77  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopHttpClient.java
  CC=  10  Cog=   26  Nest= 6  Fns=  4  Lines=   83  src/main/java/com/tsoft/lantliv/prestashop/json/api/PricewatchStockApi.java
  CC=  21  Cog=   25  Nest= 4  Fns=  5  Lines=  198  src/main/java/com/tsoft/lantliv/prestashop/old/Item.java
  CC=  14  Cog=   21  Nest= 3  Fns=  5  Lines=   67  src/main/java/com/tsoft/lantliv/common/FileUtils.java

TOP 10 — DEEPEST NESTING
  CC=   2  Cog=   11  Nest=12  Fns=  6  Lines=  203  src/test/java/com/tsoft/lantliv/prestashop/jsonapi/JSONParsingTest.java
  CC=  10  Cog=   33  Nest= 8  Fns=  1  Lines=   78  src/main/java/com/tsoft/lantliv/tools/UpdateAllSupplierIDsInLantliv.java
  CC=  61  Cog=  132  Nest= 7  Fns= 13  Lines=  355  src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java
  CC=  13  Cog=   31  Nest= 6  Fns=  2  Lines=   85  src/main/java/com/tsoft/lantliv/tools/ActivateOrDeactivateProductsInLantliv.java
  CC=  10  Cog=   39  Nest= 6  Fns=  3  Lines=   92  src/main/java/com/tsoft/lantliv/prestashop/json/api/PricewatchHttpClient.java
  CC=  10  Cog=   26  Nest= 6  Fns=  4  Lines=   83  src/main/java/com/tsoft/lantliv/prestashop/json/api/PricewatchStockApi.java
  CC=  14  Cog=   34  Nest= 5  Fns=  5  Lines=  165  src/main/java/com/tsoft/lantliv/common/PostgreSQLHelper.java
  CC=  11  Cog=   20  Nest= 5  Fns=  4  Lines=   73  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopCategoryApi.java
  CC=   8  Cog=   27  Nest= 5  Fns=  6  Lines=   77  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopHttpClient.java
  CC=   2  Cog=    3  Nest= 4  Fns=  1  Lines=   14  src/test/java/com/tsoft/utils/FileUtils.java

TOP 10 — MOST FUNCTIONS
  CC=   1  Cog=    0  Nest= 3  Fns= 37  Lines=  178  src/main/java/com/tsoft/lantliv/common/PGProduct.java
  CC=   1  Cog=    0  Nest= 2  Fns= 16  Lines=   82  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopXMLAPI.java
  CC=   4  Cog=    6  Nest= 3  Fns= 13  Lines=   91  src/main/java/com/tsoft/lantliv/pswebservice/PrestashopClient.java
  CC=  61  Cog=  132  Nest= 7  Fns= 13  Lines=  355  src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java
  CC=   4  Cog=    6  Nest= 3  Fns= 13  Lines=   94  src/main/java/com/tsoft/lantliv/prestashop/old/PrestashopClient.java
  CC=  21  Cog=   38  Nest= 4  Fns= 11  Lines=  110  src/main/java/com/tsoft/lantliv/common/Utils.java
  CC=  13  Cog=   19  Nest= 4  Fns= 11  Lines=  109  src/main/java/com/tsoft/lantliv/prestashop/xml/api/CategoryHelper.java
  CC=   1  Cog=    0  Nest= 2  Fns= 11  Lines=   66  src/main/java/com/tsoft/lantliv/prestashop/json/api/TSoftPrestashopJsonAPI.java
  CC=   6  Cog=   10  Nest= 3  Fns= 10  Lines=   74  src/main/java/com/tsoft/lantliv/pswebservice/StockHelper.java
  CC=   2  Cog=   11  Nest=12  Fns=  6  Lines=  203  src/test/java/com/tsoft/lantliv/prestashop/jsonapi/JSONParsingTest.java

TOP 10 — LARGEST FILES
  CC=   9  Cog=   16  Nest= 3  Fns=  0  Lines=  494  src/test/java/com/tsoft/lantliv/prestashop/xmlapi/BasicXMLParsingTest.java
  CC=  61  Cog=  132  Nest= 7  Fns= 13  Lines=  355  src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java
  CC=   2  Cog=   11  Nest=12  Fns=  6  Lines=  203  src/test/java/com/tsoft/lantliv/prestashop/jsonapi/JSONParsingTest.java
  CC=  21  Cog=   25  Nest= 4  Fns=  5  Lines=  198  src/main/java/com/tsoft/lantliv/prestashop/old/Item.java
  CC=   1  Cog=    0  Nest= 3  Fns= 37  Lines=  178  src/main/java/com/tsoft/lantliv/common/PGProduct.java
  CC=  14  Cog=   34  Nest= 5  Fns=  5  Lines=  165  src/main/java/com/tsoft/lantliv/common/PostgreSQLHelper.java
  CC=   3  Cog=    2  Nest= 3  Fns=  0  Lines=  136  src/test/java/com/tsoft/lantliv/prestashop/xmlapi/ProductApiTest.java
  CC=  10  Cog=   18  Nest= 3  Fns=  6  Lines=  121  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopProductApi.java
  CC=  21  Cog=   38  Nest= 4  Fns= 11  Lines=  110  src/main/java/com/tsoft/lantliv/common/Utils.java
  CC=  13  Cog=   19  Nest= 4  Fns= 11  Lines=  109  src/main/java/com/tsoft/lantliv/prestashop/xml/api/CategoryHelper.java

TOP 10 FUNCTIONS — HIGHEST CYCLOMATIC COMPLEXITY
  CC=  17  Cog=   16  Nest= 0  Lines=   19  isEqual  (src/main/java/com/tsoft/lantliv/prestashop/old/Item.java:99)
  CC=  16  Cog=   51  Nest= 5  Lines=   64  get  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:278)
  CC=  13  Cog=   31  Nest= 4  Lines=   64  deactivateProductsInFile  (src/main/java/com/tsoft/lantliv/tools/ActivateOrDeactivateProductsInLantliv.java:28)
  CC=  10  Cog=   33  Nest= 6  Lines=   64  main  (src/main/java/com/tsoft/lantliv/tools/UpdateAllSupplierIDsInLantliv.java:25)
  CC=   9  Cog=    2  Nest= 1  Lines=   16  checkStatusCode  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:112)
  CC=   9  Cog=   19  Nest= 3  Lines=   33  add  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:208)
  CC=   9  Cog=   15  Nest= 1  Lines=   30  edit  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:411)
  CC=   9  Cog=   24  Nest= 4  Lines=   43  updateStockForProduct  (src/main/java/com/tsoft/lantliv/prestashop/json/api/PricewatchStockApi.java:54)
  CC=   8  Cog=   18  Nest= 2  Lines=   31  head  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:364)
  CC=   8  Cog=   27  Nest= 4  Lines=   30  execute  (src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopHttpClient.java:58)

TOP 10 FUNCTIONS — HIGHEST COGNITIVE COMPLEXITY
  CC=  16  Cog=   51  Nest= 5  Lines=   64  get  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:278)
  CC=  10  Cog=   33  Nest= 6  Lines=   64  main  (src/main/java/com/tsoft/lantliv/tools/UpdateAllSupplierIDsInLantliv.java:25)
  CC=  13  Cog=   31  Nest= 4  Lines=   64  deactivateProductsInFile  (src/main/java/com/tsoft/lantliv/tools/ActivateOrDeactivateProductsInLantliv.java:28)
  CC=   8  Cog=   27  Nest= 4  Lines=   30  execute  (src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopHttpClient.java:58)
  CC=   9  Cog=   24  Nest= 4  Lines=   43  updateStockForProduct  (src/main/java/com/tsoft/lantliv/prestashop/json/api/PricewatchStockApi.java:54)
  CC=   9  Cog=   19  Nest= 3  Lines=   33  add  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:208)
  CC=   7  Cog=   19  Nest= 2  Lines=   62  store  (src/main/java/com/tsoft/lantliv/common/PostgreSQLHelper.java:116)
  CC=   8  Cog=   18  Nest= 2  Lines=   31  head  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:364)
  CC=  17  Cog=   16  Nest= 0  Lines=   19  isEqual  (src/main/java/com/tsoft/lantliv/prestashop/old/Item.java:99)
  CC=   9  Cog=   15  Nest= 1  Lines=   30  edit  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:411)

TOP 10 FUNCTIONS — DEEPEST NESTING
  CC=   1  Cog=    0  Nest= 9  Lines=    9  testParsingOfStockList  (src/test/java/com/tsoft/lantliv/prestashop/jsonapi/JSONParsingTest.java:21)
  CC=  10  Cog=   33  Nest= 6  Lines=   64  main  (src/main/java/com/tsoft/lantliv/tools/UpdateAllSupplierIDsInLantliv.java:25)
  CC=  16  Cog=   51  Nest= 5  Lines=   64  get  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:278)
  CC=  13  Cog=   31  Nest= 4  Lines=   64  deactivateProductsInFile  (src/main/java/com/tsoft/lantliv/tools/ActivateOrDeactivateProductsInLantliv.java:28)
  CC=   8  Cog=   27  Nest= 4  Lines=   30  execute  (src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopHttpClient.java:58)
  CC=   4  Cog=   13  Nest= 4  Lines=   22  get  (src/main/java/com/tsoft/lantliv/prestashop/json/api/PricewatchHttpClient.java:31)
  CC=   4  Cog=   13  Nest= 4  Lines=   24  post  (src/main/java/com/tsoft/lantliv/prestashop/json/api/PricewatchHttpClient.java:54)
  CC=   4  Cog=   13  Nest= 4  Lines=   24  patch  (src/main/java/com/tsoft/lantliv/prestashop/json/api/PricewatchHttpClient.java:79)
  CC=   9  Cog=   24  Nest= 4  Lines=   43  updateStockForProduct  (src/main/java/com/tsoft/lantliv/prestashop/json/api/PricewatchStockApi.java:54)
  CC=   5  Cog=    9  Nest= 3  Lines=   33  executeRequest  (src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java:144)

==============================================================
  OVERALL HEALTH:  4.5/5.0   ★★★★☆
==============================================================

  Good overall health. The codebase has manageable complexity.

  1 file(s) in cyclomatic band 51–100 — prioritize refactoring.

  1 file(s) exceed cognitive >100 (aggregate) — severe complexity; treat as refactor targets.

  2 file(s) with nesting depth 7–9 — consider flattening or helpers.

  1 file(s) exceed nesting depth >9 — pathological structure; flatten aggressively.

```

