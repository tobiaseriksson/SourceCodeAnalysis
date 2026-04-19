# Sample output of Logging Analysis script 


```
python ../SourceCodeAnalysis/logging_analysis.py 

  Scanning: /Users/tobiaseriksson/Softhouse/CommonLantlivUtils

==============================================================
  LOGGING USAGE ANALYSIS
==============================================================

OVERVIEW
  Files analyzed:        83
  Files with logging:    28  (34%)
  Code lines:            4,858
  Active log lines:      155
  Commented log lines:   5
  Log density:           3.19%  (1 log line per 31 code lines)

BY LOG LEVEL (active only)
  error       49  ( 31.6%)  ███████████████
  warn         6  (  3.9%)  █
  info        85  ( 54.8%)  ███████████████████████████
  debug       15  (  9.7%)  ████
  trace        0  (  0.0%)  

BY LOGGING FRAMEWORK / API
  console                 81  ( 52.3%)
  SLF4J                   74  ( 47.7%)

TOP 10 FILES — MOST LOG LINES
    15 logs  ( 13.8%)  [info=15]  src/main/java/com/tsoft/lantliv/prestashop/xml/api/CategoryHelper.java
       via: console=15
    13 logs  ( 10.7%)  [debug=6  error=6  info=1]  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopProductApi.java
       via: SLF4J=13
    12 logs  ( 14.1%)  [error=2  info=10]  src/main/java/com/tsoft/lantliv/tools/ActivateOrDeactivateProductsInLantliv.java
       via: console=12
    12 logs  ( 15.4%)  [error=3  info=5  warn=4]  src/main/java/com/tsoft/lantliv/tools/UpdateAllSupplierIDsInLantliv.java
       via: SLF4J=12
    10 logs  (  2.8%)  [error=3  info=7]  src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java
       via: console=10
     8 logs  ( 10.8%)  [error=2  info=6]  src/main/java/com/tsoft/lantliv/pswebservice/StockHelper.java
       via: SLF4J=2, console=6
     8 logs  ( 11.0%)  [debug=3  error=5]  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopCategoryApi.java
       via: SLF4J=8
     7 logs  ( 10.4%)  [debug=1  error=6]  src/main/java/com/tsoft/lantliv/common/FileUtils.java
       via: SLF4J=5, console=2
     7 logs  ( 12.1%)  [error=1  info=6]  src/main/java/com/tsoft/lantliv/common/ChecksumUtils.java
       via: console=7
     6 logs  (  7.1%)  [info=6]  src/test/java/com/tsoft/lantliv/prestashop/jsonapi/ProductJsonApiTest.java
       via: console=6

TOP 10 FILES — HIGHEST LOG DENSITY
   15.4%  (  4 /    26 lines)  src/main/java/com/tsoft/lantliv/selenium/WebParsingErrors.java
   15.4%  ( 12 /    78 lines)  src/main/java/com/tsoft/lantliv/tools/UpdateAllSupplierIDsInLantliv.java
   14.1%  ( 12 /    85 lines)  src/main/java/com/tsoft/lantliv/tools/ActivateOrDeactivateProductsInLantliv.java
   13.8%  ( 15 /   109 lines)  src/main/java/com/tsoft/lantliv/prestashop/xml/api/CategoryHelper.java
   12.1%  (  7 /    58 lines)  src/main/java/com/tsoft/lantliv/common/ChecksumUtils.java
   11.0%  (  8 /    73 lines)  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopCategoryApi.java
   10.8%  (  8 /    74 lines)  src/main/java/com/tsoft/lantliv/pswebservice/StockHelper.java
   10.7%  ( 13 /   121 lines)  src/main/java/com/tsoft/lantliv/prestashop/xml/api/PrestashopProductApi.java
   10.4%  (  7 /    67 lines)  src/main/java/com/tsoft/lantliv/common/FileUtils.java
    9.5%  (  2 /    21 lines)  src/main/java/com/tsoft/lantliv/selenium/CustomHtmlUnitDriver.java

FILES WITH COMMENTED-OUT LOG LINES (5 total)
    4 commented  src/main/java/com/tsoft/lantliv/tools/UpdateAllSupplierIDsInLantliv.java
    1 commented  src/main/java/com/tsoft/lantliv/pswebservice/PSWebServiceClient.java

==============================================================
  LOG DENSITY: 3.19%  →  Moderate — reasonable logging coverage
==============================================================

```

