# BOLT'S JOURNAL - CRITICAL LEARNINGS

## Philosophy
- Speed is a feature
- Every millisecond counts
- Measure first, optimize second
- Don't sacrifice readability for micro-optimizations

## Learnings
## 2024-05-23 - Replaced ORDER BY RAND() with PHP Shuffle
**Learning:** SQL 'ORDER BY RAND()' is a performance killer on large tables as it forces a temporary table scan.
**Action:** Always fetch a pool of IDs, shuffle in PHP, and cache the result.
