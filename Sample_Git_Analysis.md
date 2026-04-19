
# Sample output of the git analysis script

```
python ../SourceCodeAnalysis/analyze_commits.py 
Fetching git history in /Users/tobiaseriksson/Softhouse/CommonLantlivUtils (this takes a few seconds)...

Total unique commits: 16
Total unique files: 121

================================================================================
TOP 20 MOST FREQUENTLY CHANGED FILES (BY COMMITS)
================================================================================
Rank  Commits   File
--------------------------------------------------------------------------------
1     11        pom.xml
2     5         src/main/java/com/tsoft/lantliv/prestashop/json/api/TSoftPrestashopJsonAPI.java
3     5         src/main/java/com/tsoft/lantliv/common/PostgreSQLHelper.java
4     5         src/main/java/com/tsoft/lantliv/common/Utils.java
5     4         src/main/java/com/tsoft/lantliv/tools/ActivateOrDeactivateProductsInLantliv.java
6     4         src/test/java/com/tsoft/lantliv/prestashop/xmlapi/APITest.java
7     3         src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopApiFacade.java
8     3         src/main/java/com/tsoft/lantliv/tools/UpdateAllSupplierIDsInLantliv.java
9     3         src/main/java/com/tsoft/lantliv/prestashop/xml/api/CategoryHelper.java
10    3         src/test/java/com/tsoft/lantliv/prestashop/xmlapi/CategoryHelperTest.java
11    3         src/test/java/com/tsoft/lantliv/prestashop/xmlapi/PrestashopCategoryHelper.java
12    3         src/test/java/com/tsoft/lantliv/prestashop/xmlapi/BasicXMLParsingTest.java
13    2         src/test/java/com/tsoft/lantliv/prestashop/json/api/APITest.java
14    2         src/test/java/com/tsoft/lantliv/prestashop/jsonapi/APITest.java
15    2         src/test/java/com/tsoft/lantliv/prestashop/jsonapi/JSONParsingTest.java
16    2         src/main/java/com/tsoft/lantliv/prestashop/xml/common/associations.java
17    2         src/test/java/com/tsoft/lantliv/prestashop/xmlapi/CategoryXMLParsingTest.java
18    2         .idea/misc.xml
19    2         src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopAPI.java
20    2         src/main/java/com/tsoft/lantliv/prestashop/xml/common/basicproduct.java

================================================================================
TOP 20 MOST FREQUENTLY CHANGED FILES (BY LINES OF CODE)
================================================================================
Rank  Total L/C   Added     Deleted   File
--------------------------------------------------------------------------------
1     14326       +14326    -0        src/test/resources/categories.xml
2     1656        +828      -828      Gallager.csv
3     652         +585      -67       src/test/java/com/tsoft/lantliv/prestashop/xmlapi/BasicXMLParsingTest.java
4     561         +561      -0        src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java
5     458         +102      -356      src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopXMLAPI.java
6     454         +271      -183      src/main/java/com/tsoft/lantliv/prestashop/json/api/TSoftPrestashopJsonAPI.java
7     430         +417      -13       src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopAPI.java
8     418         +209      -209      src/test/java/com/tsoft/lantliv/prestashop/xmlapi/APITest.java
9     368         +184      -184      src/test/java/com/tsoft/lantliv/prestashop/jsonapi/APITest.java
10    279         +204      -75       pom.xml
11    232         +116      -116      src/test/java/com/tsoft/lantliv/prestashop/xmlapi/PrestashopCategoryHelper.java
12    231         +230      -1        src/test/java/com/tsoft/lantliv/prestashop/jsonapi/JSONParsingTest.java
13    219         +219      -0        src/main/java/com/tsoft/lantliv/prestashop/old/Lantliv.java
14    216         +216      -0        src/main/java/com/tsoft/lantliv/prestashop/old/OldProduct.java
15    214         +214      -0        src/main/java/com/tsoft/lantliv/prestashop/old/Item.java
16    209         +156      -53       src/main/java/com/tsoft/lantliv/tools/ActivateOrDeactivateProductsInLantliv.java
17    206         +194      -12       src/main/java/com/tsoft/lantliv/common/PostgreSQLHelper.java
18    164         +149      -15       src/main/java/com/tsoft/lantliv/common/Utils.java
19    151         +147      -4        src/main/java/com/tsoft/lantliv/prestashop/xml/api/CategoryHelper.java
20    141         +141      -0        src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopProductApi.java

================================================================================
COMMIT CATEGORIZATION
================================================================================
  feature                   7 commits ( 43.8%)
      Example: Add loadFromApi method to CategoryHelper for fetching categories from PrestaShop API; enhance tests 
      Example: Refactor PrestashopXMLAPI to deprecate old methods in favor of a new facade structure. Removed legac
      Example: Updated pom.xml to version 2.1, adjusted JDK to 21, and added new dependencies for category manageme
  bug_fix                   0 commits (  0.0%)
  refactoring               5 commits ( 31.2%)
      Example: Remove unused JSON API classes and tests to streamline the codebase, enhancing maintainability and r
      Example: Remove unused imports and clean up code in associations.java for improved readability.
      Example: tidy up before bigger refactoring of the XML API
  other                     4 commits ( 25.0%)
      Example: rewrote the deactivate products function
      Example: updated lombok version to 1.18.38 and improved utils.toBigDecimal() to be more resilient
      Example: improved cleanupName so that it does not try to change words that are less than 4 ch or starts with 

  TOTAL                    16 commits

================================================================================
MOST POPULAR CODERS (by unique commits)
================================================================================
Rank  Commits   Percentage  Author
--------------------------------------------------------------------------------
1     16        100.0%       Tobias Eriksson

================================================================================
COMMITS BY YEAR
================================================================================
  Year      Commits   Added     Deleted   Total L/C   Trend
  ------------------------------------------------------------------------------
  2025      10        +6064     -967      7031        ██
  2026      6         +16998    -1254     18252       █

================================================================================
CODE AGE (share of current lines by last modification)
================================================================================

  Each file's lines at HEAD are assigned to the latest commit that touched that file
  (non-merge history). This approximates how stale code is; it is not per-line blame.

  Grouping: calendar month of last file change (6 months ≤ repository age < 2 years).
  Repository span (oldest commit → now): 448 days.

  Reference time: 2026-04-19T15:09:12.460678+00:00 (UTC)
  Total lines counted: 20,841

  Period                                          Lines      Share
  ----------------------------------------------------------------
  2025-01 (last change)                           2,254      10.8%  █████
  2025-02 (last change)                              74       0.4%  █
  2025-09 (last change)                             163       0.8%  █
  2025-10 (last change)                              33       0.2%  █
  2025-11 (last change)                             401       1.9%  █
  2026-03 (last change)                          17,916      86.0%  ███████████████████████████████████████████

================================================================================
TOP MODULES PER CODE AGE BUCKET (by lines in bucket)
================================================================================

  Module = directory path without filename (same as COMMITS PER MODULE). Share is % of lines within that bucket.


  2025-01 (last change)
  Bucket: 2,254 lines (10.8% of repository)
  Rank       Lines   % of bucket  Module
  ------------------------------------------------------------------------
  1            967         42.9%  src/main/java/com/tsoft/lantliv/pswebservice
  2            544         24.1%  src/main/java/com/tsoft/lantliv/prestashop/old
  3            402         17.8%  src/main/java/com/tsoft/lantliv/prestashop/xml/…
  4            205          9.1%  src/main/java/com/tsoft/lantliv/common
  5             58          2.6%  src/main/java/com/tsoft/lantliv/selenium

  2025-02 (last change)
  Bucket: 74 lines (0.4% of repository)
  Rank       Lines   % of bucket  Module
  ------------------------------------------------------------------------
  1             55         74.3%  src/test/java/com/tsoft/lantliv/common
  2             19         25.7%  src/test/java/com/tsoft/lantliv/prestashop/chec…

  2025-09 (last change)
  Bucket: 163 lines (0.8% of repository)
  Rank       Lines   % of bucket  Module
  ------------------------------------------------------------------------
  1            134         82.2%  src/main/java/com/tsoft/lantliv/common
  2             29         17.8%  src/main/resources

  2025-10 (last change)
  Bucket: 33 lines (0.2% of repository)
  Rank       Lines   % of bucket  Module
  ------------------------------------------------------------------------
  1             24         72.7%  .idea
  2              9         27.3%  (root)

  2025-11 (last change)
  Bucket: 401 lines (1.9% of repository)
  Rank       Lines   % of bucket  Module
  ------------------------------------------------------------------------
  1            401        100.0%  src/main/java/com/tsoft/lantliv/common

  2026-03 (last change)
  Bucket: 17,916 lines (86.0% of repository)
  Rank       Lines   % of bucket  Module
  ------------------------------------------------------------------------
  1         14,326         80.0%  src/test/resources
  2            921          5.1%  src/test/java/com/tsoft/lantliv/prestashop/xmla…
  3            828          4.6%  src/main/java/com/tsoft/lantliv/prestashop/xml/…
  4            451          2.5%  src/test/java/com/tsoft/lantliv/prestashop/json…
  5            401          2.2%  src/main/java/com/tsoft/lantliv/prestashop/json…

================================================================================
BUG FIXES VS FEATURES/IMPROVEMENTS OVER TIME (by month)
================================================================================
  Month          Bugs   Features Bug Bar                   Feature Bar
  ------------------------------------------------------------------------------
  2025-Jan          0          1                             🟢
  2025-Feb          0          2                             🟢🟢
  2025-Oct          0          1                             🟢
  2026-Mar          0          3                             🟢🟢🟢

                              --- Yearly Summary ---                            
  Year           Bugs   Features  Ratio (B/F)
  ------------------------------------------
  2025              0          4         0.00
  2026              0          3         0.00

================================================================================
COMMITS PER MODULE (based on path)
================================================================================

  Total unique modules: 25
  Rank  Commits   Percentage  Module
  --------------------------------------------------------------------------
  1     11         15.9%       (root)  █
  2     7          10.1%       src/main/java/com/tsoft/lantliv/common  
  3     6           8.7%       src/main/java/com/tsoft/lantliv/prestashop/json/api  
  4     6           8.7%       src/main/java/com/tsoft/lantliv/prestashop/xml/api  
  5     5           7.2%       src/main/java/com/tsoft/lantliv/tools  
  6     5           7.2%       src/test/java/com/tsoft/lantliv/prestashop/xmlapi  
  7     3           4.3%       src/main/java/com/tsoft/lantliv/prestashop/xml/common  
  8     3           4.3%       .idea  
  9     3           4.3%       src/test/java/com/tsoft/lantliv/common  
  10    2           2.9%       src/test/java/com/tsoft/lantliv/prestashop/json/api  
  11    2           2.9%       src/test/java/com/tsoft/lantliv/prestashop/jsonapi  
  12    2           2.9%       src/main/java/com/tsoft/lantliv/prestashop/old  
  13    2           2.9%       src/test/java/com/tsoft/lantliv  
  14    1           1.4%       src/main/java/com/tsoft/lantliv/prestashop/json/{api => common}  
  15    1           1.4%       src/test/java/com/tsoft/lantliv/prestashop/xml/common  
  16    1           1.4%       src/test/java/com/tsoft/utils  
  17    1           1.4%       src/test/resources  
  18    1           1.4%       src/main/java/com/tsoft/lantliv/{prestashop/old => common}  
  19    1           1.4%       src/main/resources  
  20    1           1.4%       src/test/java/com/tsoft/lantliv/prestashop/checksum  
  21    1           1.4%       .idea/codeStyles  
  22    1           1.4%       .mvn  
  23    1           1.4%       src/main/java/com/tsoft/lantliv  
  24    1           1.4%       src/main/java/com/tsoft/lantliv/pswebservice  
  25    1           1.4%       src/main/java/com/tsoft/lantliv/selenium  

================================================================================
BUG FIXES PER MODULE (Top 20)
================================================================================

  Rank  Bug Fixes   Percentage  Module
  --------------------------------------------------------------------------

================================================================================
FEATURES PER MODULE (Top 20)
================================================================================

  Rank  Features    Percentage  Module
  --------------------------------------------------------------------------
  1     5            16.1%       (root)  ██
  2     4            12.9%       src/test/java/com/tsoft/lantliv/prestashop/xmlapi  ██
  3     3             9.7%       src/main/java/com/tsoft/lantliv/prestashop/json/api  █
  4     3             9.7%       src/main/java/com/tsoft/lantliv/prestashop/xml/api  █
  5     2             6.5%       .idea  █
  6     2             6.5%       src/main/java/com/tsoft/lantliv/common  █
  7     2             6.5%       src/test/java/com/tsoft/lantliv/common  █
  8     1             3.2%       src/main/java/com/tsoft/lantliv/tools  
  9     1             3.2%       src/test/java/com/tsoft/lantliv/prestashop/json/api  
  10    1             3.2%       src/test/java/com/tsoft/lantliv/prestashop/jsonapi  
  11    1             3.2%       src/main/java/com/tsoft/lantliv/prestashop/xml/common  
  12    1             3.2%       src/test/java/com/tsoft/lantliv/prestashop/xml/common  
  13    1             3.2%       src/test/java/com/tsoft/utils  
  14    1             3.2%       src/test/resources  
  15    1             3.2%       src/main/java/com/tsoft/lantliv/prestashop/old  
  16    1             3.2%       src/test/java/com/tsoft/lantliv  
  17    1             3.2%       src/test/java/com/tsoft/lantliv/prestashop/checksum  

Results saved to commit_analysis_results.json
```