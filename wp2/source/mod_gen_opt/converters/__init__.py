"""Instance conversion utilities for transforming standard benchmark formats to OptDSL.

Provides reusable conversion scripts for:
  - CVRP (convert_cvrp.py): CVRP Library and Christofides/Eilon .vrp format → .dsl
    (handles EUC_2D coordinates and EXPLICIT/LOWER_ROW distance matrices;
    supports vehicle count from header, filename E-n*-k*, or manual override)
  - 2D Bin Packing (convert_2dbp.py): Standard .txt format → .dsl
  - JSSP (convert_jssp.py): Standard JSSP .txt format → .dsl

Each module can be run standalone (CLI mode) or imported as a library.

Typical workflow:
  1. Download benchmark instances in native format
  2. Use converters to batch-convert to .dsl format
  3. Use converted instances in mod_gen_opt benchmark suite
"""
