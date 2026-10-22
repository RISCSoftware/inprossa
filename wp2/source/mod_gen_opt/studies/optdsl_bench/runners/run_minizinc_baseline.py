#!/usr/bin/env python
"""MiniZinc baseline solver wrapper for benchmark comparison.

Loads OptDSL instances (.dsl format), translates to MiniZinc, runs solver,
and outputs results in JSON format for benchmark comparison.

Usage:
  python run_minizinc_baseline.py instance.dsl --timeout 60 --output result.json
  
Output JSON format:
  {
    "instance": "instance.dsl",
    "objective": 1234.5,
    "objective_bound": 1000.0,
    "status": "OPTIMAL_FOUND" or "TIME_LIMIT" or "ERROR",
    "runtime_seconds": 45.2,
    "nSolutions": 5,
    "error": null or error message
  }
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def run_minizinc_solver(
    dsl_file: str,
    timeout_seconds: float = 60.0,
) -> dict:
    """Run MiniZinc solver on a .dsl instance with timeout.
    
    Args:
        dsl_file: Path to .dsl file
        timeout_seconds: Solver timeout in seconds
    
    Returns:
        Dict with result: {objective, bound, status, runtime_seconds, nSolutions}
    """
    result = {
        "objective": None,
        "objective_bound": None,
        "status": "ERROR",
        "runtime_seconds": 0.0,
        "nSolutions": 0,
        "error": None,
    }
    
    dsl_path = Path(dsl_file)
    if not dsl_path.exists():
        result["error"] = f"File not found: {dsl_file}"
        return result
    
    try:
        # Read DSL file
        dsl_code = dsl_path.read_text(encoding="utf-8")
        
        # Try to import and run MiniZinc translator
        # Note: This requires the minizinc package to be installed
        # and the src module to be available in the Python path
        try:
            # Attempt to import MiniZinc translator from src
            import sys
            src_path = Path(__file__).parent.parent / "minizinc" / "src"
            if src_path.exists():
                sys.path.insert(0, str(src_path.parent))
            
            from src import MiniZincTranslator
        except (ImportError, ModuleNotFoundError) as e:
            result["error"] = f"MiniZinc translator not available: {e}. Install minizinc or ensure src module is in path."
            result["status"] = "SETUP_ERROR"
            return result
        
        # Translate and run with timeout
        start_time = time.perf_counter()
        try:
            translator = MiniZincTranslator(dsl_code)
            
            # Run solver with timeout
            # Note: MiniZincTranslator internals may not directly support timeout
            # For now, we'll run it and track elapsed time
            solution = translator.solve()
            
            elapsed = time.perf_counter() - start_time
            result["runtime_seconds"] = elapsed
            
            if solution is not None:
                # Extract objective value and bound if available
                if isinstance(solution, dict):
                    result["objective"] = solution.get("objective")
                    result["objective_bound"] = solution.get("objective_bound", result["objective"])
                    result["nSolutions"] = solution.get("nSolutions", 1)
                    result["status"] = "OPTIMAL_FOUND" if solution.get("status") == "OPTIMAL" else "FEASIBLE_FOUND"
                else:
                    result["objective"] = float(solution)
                    result["status"] = "FEASIBLE_FOUND"
            else:
                result["status"] = "NO_SOLUTION"
        
        except TimeoutError:
            elapsed = time.perf_counter() - start_time
            result["runtime_seconds"] = min(elapsed, timeout_seconds)
            result["status"] = "TIME_LIMIT"
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            result["runtime_seconds"] = elapsed
            result["error"] = str(e)
            result["status"] = "SOLVER_ERROR"
    
    except Exception as e:
        result["error"] = str(e)
        result["status"] = "ERROR"
    
    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MiniZinc baseline solver for benchmark comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "instance",
        help="Path to .dsl instance file",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        dest="timeout_seconds",
        help="Solver timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file (default: stdout)",
    )
    
    args = parser.parse_args()
    
    # Check instance file exists
    instance_path = Path(args.instance)
    if not instance_path.exists():
        print(f"ERROR: Instance file not found: {args.instance}", file=sys.stderr)
        sys.exit(1)
    
    # Run solver
    result = run_minizinc_solver(str(instance_path), timeout_seconds=args.timeout_seconds)
    
    # Add instance name to result
    result["instance"] = instance_path.name
    
    # Output result
    output_json = json.dumps(result, indent=2)
    
    if args.output:
        args.output.write_text(output_json, encoding="utf-8")
        print(f"Result written to: {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
