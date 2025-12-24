## 2025-12-24 - [Optimizing Random Product Queries]
**Learning:** `ORDER BY RAND()` is a major performance killer in WordPress/WooCommerce product queries.
**Action:** Replace it with a strategy of fetching a candidate pool of IDs (e.g., 50), shuffling in PHP, and caching the result using transients. This reduces DB load from O(N*logN) to effectively O(1) for cached hits.
