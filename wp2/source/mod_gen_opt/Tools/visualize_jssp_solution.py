"""Visualize JSSP (Job Shop Scheduling Problem) solutions as HTML Gantt charts."""

from __future__ import annotations

import argparse
import ast
import html
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class OperationInfo:
    job: int
    operation: int
    machine: int
    start_time: int
    end_time: int
    processing_time: int


def _read_text_with_fallback(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    # Check for BOM first — avoids mis-decoding a plain UTF-8/ASCII file as UTF-16.
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    # No BOM: try UTF-8 first (normal DSL / source files), then fallbacks.
    for enc in ("utf-8", "utf-8-sig", "cp1252", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("fallback-decode", raw, 0, 1, "Could not decode file")


def _parse_int_constant(name: str, text: str) -> int | None:
    pattern = f"{name}\\s*:\\s*int\\s*=\\s*(\\d+)"
    match = _re_search(pattern, text)
    if match:
        return int(match.group(1))
    return None


def _parse_int_list(name: str, text: str) -> list[int] | None:
    pattern = f"{name}\\s*:\\s*DSList\\([^)]+\\)\\s*=\\s*\\[([^\\]]+)\\]"
    match = _re_search(pattern, text)
    if not match:
        # Try simple format: NAME = [val1, val2, ...]
        pattern = f"{name}\\s*=\\s*\\[([^\\]]+)\\]"
        match = _re_search(pattern, text)
    if match:
        content = match.group(1)
        values = []
        for item in content.split(","):
            item = item.strip()
            if item.isdigit() or (item.startswith("-") and item[1:].isdigit()):
                values.append(int(item))
        return values if values else None
    return None


def _parse_nested_int_list(name: str, text: str) -> list[list[int]] | None:
    pattern = f"{name}\\s*:\\s*DSList[^=]*=\\s*\\["
    match = _re_search(pattern, text)
    if match:
        start = match.start()
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    block = text[start:i + 1]
                    return _parse_nested_array(block)
    return None


def _parse_nested_array(block: str) -> list[list[int]]:
    lines = []
    current_line = []
    depth = 0
    num_str = ""
    for ch in block:
        if ch == "[":
            if depth == 1 and num_str:
                if current_line:
                    lines.append([int(x) for x in current_line])
                current_line = []
            depth += 1
            num_str = ""
        elif ch == "]":
            if num_str.strip():
                current_line.append(int(num_str.strip()))
            if depth == 2 and current_line:
                lines.append([int(x) for x in current_line])
                current_line = []
            depth -= 1
            num_str = ""
        elif ch.isdigit() or ch == "-" or ch == " ":
            if ch.isdigit() or (ch == "-" and num_str == ""):
                num_str += ch
            elif num_str and ch == ",":
                current_line.append(int(num_str.strip()))
                num_str = ""
        elif ch == ",":
            if num_str.strip():
                current_line.append(int(num_str.strip()))
                num_str = ""
    return lines


def _re_search(pattern: str, text: str):
    import re
    return re.search(pattern, text, re.MULTILINE)


def _parse_nested_int_list_simple(name: str, text: str) -> list[list[int]] | None:
    """Fallback parser for nested int lists with nested brackets."""
    try:
        import re
        # Find the variable definition
        pattern = rf'{name}\s*:\s*DSList\([^)]+\)\s*=\s*(.+)'
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return None
        block = match.group(1).strip()
        
        # Parse the nested structure
        result: list[list[int]] = []
        current_row: list[int] = []
        depth = 0
        num = ""
        
        for ch in block:
            if ch == "[":
                if depth == 0:
                    depth = 1
                elif depth >= 1:
                    depth += 1
                    num = ""
            elif ch == "]":
                if num.strip():
                    current_row.append(int(num.strip()))
                    num = ""
                if depth == 2:
                    result.append(current_row)
                    current_row = []
                depth -= 1
            elif ch.isdigit() or (ch == "-" and num == ""):
                num += ch
            elif ch == ",":
                if num.strip():
                    current_row.append(int(num.strip()))
                    num = ""
        
        return result if result else None
    except Exception:
        return None


def _find_nested_bracketed_block(var_name: str, text: str) -> str | None:
    """Find a [...] block after a variable definition NAME = [...] or NAME : type = [...].
    
    Handles DSList(N_JOBS, DSList(N_MACHINES, ...)) type annotations correctly.
    """
    import re
    
    var_re = rf'\b{re.escape(var_name)}\b'
    for var_m in re.finditer(var_re, text):
        var_pos = var_m.start()
        
        # Check not in a comment
        line_start = text.rfind('\n', 0, var_pos) + 1
        line_prefix = text[line_start:var_pos]
        if line_prefix.strip().startswith('#'):
            continue
        
        # Look for '=' after this position (not '[', which would be array indexing)
        search_start = var_m.end()
        
        # Find '=' while handling nested parentheses from DSList types
        paren_depth = 0
        eq_idx = -1
        for i in range(search_start, len(text)):
            ch = text[i]
            if ch == '(':
                paren_depth += 1
            elif ch == ')':
                paren_depth -= 1
            elif ch == '=' and paren_depth == 0:
                eq_idx = i
                break
        
        if eq_idx < 0:
            continue
        
        # Skip to after the '=' and any whitespace to find '['
        i = eq_idx + 1
        while i < len(text) and text[i] in ' \t\n':
            i += 1
        
        if i >= len(text) or text[i] != '[':
            continue
        
        # Count bracket depth to find matching ']'
        depth = 1
        i += 1
        in_str = False
        str_ch = None
        
        while i < len(text) and depth > 0:
            ch = text[i]
            if not in_str:
                if ch in '"\'':
                    in_str = True
                    str_ch = ch
                elif ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
            else:
                if ch == '\\' and i + 1 < len(text):
                    i += 2
                    continue
                elif ch == str_ch:
                    in_str = False
                    str_ch = None
            i += 1
        
        if depth == 0:
            return text[eq_idx + 1:i]
    
    return None


def parse_instance_data(dsl_text: str) -> dict[str, Any]:
    """Parse JSSP instance data from DSL text."""
    import re
    
    n_jobs = _parse_int_constant("N_JOBS", dsl_text)
    n_machines = _parse_int_constant("N_MACHINES", dsl_text)
    
    if n_jobs is None or n_machines is None:
        raise ValueError("Could not find N_JOBS or N_MACHINES constants")
    
    pt_block = _find_nested_bracketed_block("PROCESSING_TIMES", dsl_text)
    pt_matrix = _parse_nested_array(pt_block) if pt_block else None
    
    ms_block = _find_nested_bracketed_block("MACHINE_SEQUENCE", dsl_text)
    ms_matrix = _parse_nested_array(ms_block) if ms_block else None
    
    if pt_matrix is None or ms_matrix is None:
        raise ValueError("Could not parse PROCESSING_TIMES or MACHINE_SEQUENCE")
    
    return {
        "n_jobs": n_jobs,
        "n_machines": n_machines,
        "processing_times": pt_matrix,
        "machine_sequence": ms_matrix,
    }


def parse_solution_data(dsl_text: str) -> dict[str, Any]:
    """Parse solution (completion times) from DSL text with warm start hints."""
    try:
        tree = ast.parse(dsl_text)
    except SyntaxError:
        raise ValueError("Could not parse DSL file as Python AST")
    
    warm_start: dict[str, Any] | None = None
    
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            is_ws = (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
                and decorator.func.id == "warm_start"
            ) or (
                isinstance(decorator, ast.Name)
                and decorator.id == "warm_start"
            )
            if not is_ws:
                continue
            
            for stmt in node.body:
                if isinstance(stmt, ast.Return) and stmt.value is not None:
                    try:
                        warm_start = ast.literal_eval(stmt.value)
                    except:
                        pass
    
    if warm_start is None:
        raise ValueError("No @warm_start decorator found in DSL file")
    
    return warm_start


def parse_completion_times(solution: dict[str, Any], n_jobs: int, n_machines: int, ms_matrix: list[list[int]]) -> list[OperationInfo]:
    """Extract operation info from completion time matrix.
    
    completion[job][op] = completion time of operation op of job job
    
    We compute start_time = completion_time - processing_time
    """
    operations: list[OperationInfo] = []
    
    completion = solution.get("completion", [])
    if not isinstance(completion, list) or len(completion) != n_jobs:
        # Try alternative format: completion_0, completion_1, etc.
        for j in range(n_jobs):
            row_key = f"completion_{j}"
            if row_key in solution:
                row = solution[row_key]
                if isinstance(row, list):
                    for op in range(min(n_machines, len(row))):
                        machine = ms_matrix[j][op] if j < len(ms_matrix) and op < len(ms_matrix[j]) else op
                        end_time = int(row[op]) if row[op] is not None else 0
                        operations.append(OperationInfo(
                            job=j, operation=op, machine=machine,
                            start_time=end_time, end_time=end_time,
                            processing_time=0
                        ))
        return operations
    
    for j in range(n_jobs):
        if not isinstance(completion[j], list):
            continue
        row = completion[j]
        for op in range(min(n_machines, len(row))):
            machine = ms_matrix[j][op] if j < len(ms_matrix) and op < len(ms_matrix[j]) else op
            end_time = int(row[op]) if row[op] is not None else 0
            operations.append(OperationInfo(
                job=j, operation=op, machine=machine,
                start_time=end_time, end_time=end_time,
                processing_time=0
            ))
    
    return operations


def _compute_operation_times(operations: list[OperationInfo], pt_matrix: list[list[int]]) -> list[OperationInfo]:
    """Compute start/end times from completion times and processing times."""
    from dataclasses import replace
    
    # Sort by job and operation to get proper precedence
    ops_by_job = {}
    for op in operations:
        if op.job not in ops_by_job:
            ops_by_job[op.job] = []
        ops_by_job[op.job].append(op)
    
    result_ops = []
    for job in sorted(ops_by_job.keys()):
        job_ops = sorted(ops_by_job[job], key=lambda x: x.operation)
        prev_end = 0
        for op in job_ops:
            # Processing times in JSSP are indexed by machine, not operation index.
            pt = pt_matrix[op.job][op.machine] if op.job < len(pt_matrix) and op.machine < len(pt_matrix[op.job]) else 1
            start_time = op.end_time - pt
            start_time = max(start_time, prev_end)
            prev_end = op.end_time
            result_ops.append(OperationInfo(
                job=op.job, operation=op.operation, machine=op.machine,
                start_time=start_time, end_time=op.end_time,
                processing_time=pt
            ))
    
    return result_ops


def _palette(idx: int) -> str:
    colors = [
        "#2563eb",  # blue
        "#dc2626",  # red
        "#16a34a",  # green
        "#ca8a04",  # yellow
        "#7c3aed",  # purple
        "#0891b2",  # cyan
        "#ea580c",  # orange
        "#be123c",  # pink
        "#4d7c0f",  # lime
        "#831843",  # magenta
        "#0369a1",  # light blue
        "#a16207",  # amber
    ]
    return colors[idx % len(colors)]


def render_gantt_html(
    operations: list[OperationInfo],
    instance: dict[str, Any],
    title: str,
) -> str:
    n_jobs = instance["n_jobs"]
    n_machines = instance["n_machines"]
    
    if not operations:
        return "<html><body><h1>No operations to display</h1></body></html>"
    
    # Calculate time bounds
    max_time = max(op.end_time for op in operations)
    min_time = min(op.start_time for op in operations)
    time_span = max(1, max_time - min_time)
    
    # Chart dimensions
    chart_width = 900
    chart_height = 400
    margin_left = 80
    margin_right = 30
    margin_top = 60
    margin_bottom = 40
    gantt_height = chart_height - margin_top - margin_bottom
    machine_height = gantt_height / max(1, n_machines)
    
    # Scale for time axis
    plot_width = chart_width - margin_left - margin_right
    
    def sx(t: int) -> float:
        return margin_left + (t - min_time) * plot_width / time_span
    
    # Build HTML
    html_parts = [f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 20px; background: #f8fafc; color: #111827; }}
    h1 {{ margin-bottom: 4px; }}
    .subtitle {{ color: #4b5563; margin-top: 0; }}
    .layout {{ display: grid; grid-template-columns: 1fr 300px; gap: 16px; }}
    .panel {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }}
    .gantt-container {{ overflow-x: auto; }}
    table {{ border-collapse: collapse; font-size: 12px; }}
    th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
    th {{ background: #f1f5f9; font-weight: 600; }}
    .swatch {{ display: inline-block; width: 12px; height: 12px; border-radius: 3px; vertical-align: middle; margin-right: 6px; }}
    .toggle-btn {{ background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 14px; cursor: pointer; font-size: 12px; }}
    .toggle-btn.active {{ background: #2563eb; color: white; border-color: #2563eb; }}
    #precedence-arrows {{ opacity: 0; transition: opacity 0.2s; pointer-events: none; }}
    #precedence-arrows.visible {{ opacity: 1; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p class="subtitle">JSSP: {n_jobs} jobs x {n_machines} machines | Makespan: {max_time}</p>  <button id="toggle-arrows" class="toggle-btn">Show Precedence</button>  
  <div class="layout">
    <div class="panel gantt-container">
      <svg width="{chart_width}" height="{chart_height}">
        <!-- Grid lines -->
"""]
    
    # Draw time grid lines
    n_ticks = min(10, max_time)
    for i in range(n_ticks + 1):
        t = min_time + int(i * time_span / n_ticks)
        x = sx(t)
        html_parts.append(f'        <line x1="{x:.1f}" y1="{margin_top}" x2="{x:.1f}" y2="{chart_height - margin_bottom}" stroke="#e5e7eb" stroke-width="1"/>')
        html_parts.append(f'        <text x="{x:.1f}" y="{chart_height - margin_bottom + 15}" text-anchor="middle" font-size="10" fill="#6b7280">{t}</text>')
    
    # Machine rows background
    for m in range(n_machines):
        y = margin_top + m * machine_height
        bg_color = "#f8fafc" if m % 2 == 0 else "#f1f5f9"
        html_parts.append(f'        <rect x="{margin_left}" y="{y}" width="{plot_width}" height="{machine_height}" fill="{bg_color}"/>')
        html_parts.append(f'        <text x="{margin_left - 10}" y="{y + machine_height/2 + 4}" text-anchor="end" font-size="11" fill="#374151">M{m}</text>')
    
    # Draw operations
    for op in operations:
        x = sx(op.start_time)
        width = max(2, sx(op.end_time) - sx(op.start_time))
        y = margin_top + op.machine * machine_height + 2
        height = machine_height - 4
        color = _palette(op.job)
        
        tooltip = f"Job {op.job}, Op {op.operation} (pt={op.processing_time})"
        html_parts.append(
            f'        <rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
            f'fill="{color}" rx="3" opacity="0.85">'
            f'<title>{html.escape(tooltip)}</title></rect>'
        )
        
        # Job label inside bar if there's room
        if width > 30:
            cx = x + width / 2
            cy = y + height / 2 + 4
            html_parts.append(
                f'        <text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" font-size="10" fill="white" font-weight="600">J{op.job}</text>'
            )
    
    # Time axis label
    html_parts.append(f'        <text x="{chart_width/2:.1f}" y="{chart_height - 5}" text-anchor="middle" font-size="11" fill="#6b7280">Time</text>')
    
    # Precedence arrows — quadratic Bézier splines from top-right of op_a to top-left of op_b,
    # with a gentle upward bow (control point slightly above the chord midpoint).
    html_parts.append('        <g id="precedence-arrows" stroke="#94a3b8" stroke-width="1.5" fill="none">')
    
    ops_by_job: dict[int, list[OperationInfo]] = {}
    for op in operations:
        ops_by_job.setdefault(op.job, []).append(op)
    
    for job in sorted(ops_by_job.keys()):
        job_ops = sorted(ops_by_job[job], key=lambda x: x.operation)
        for i in range(len(job_ops) - 1):
            op_a = job_ops[i]
            op_b = job_ops[i + 1]
            
            y_a_top = margin_top + op_a.machine * machine_height + 2
            y_b_top = margin_top + op_b.machine * machine_height + 2
            x1 = sx(op_a.end_time)
            x2 = sx(op_b.start_time)
            x2 = max(x2, x1 + 4)
            
            # Gentle upward arc: control point midway in x, ~12px above the chord
            mid_x = (x1 + x2) / 2.0
            mid_y = (y_a_top + y_b_top) / 2.0
            cp_x = mid_x
            cp_y = mid_y - 12
            path = f"M {x1:.1f},{y_a_top:.1f} Q {cp_x:.1f},{cp_y:.1f} {x2:.1f},{y_b_top:.1f}"
            html_parts.append(f'          <path d="{path}"/>')
            # Arrowhead pointing into the target bar
            html_parts.append(
                f'          <polygon points="{x2:.1f},{y_b_top:.1f} '
                f'{(x2 - 6):.1f},{(y_b_top - 4):.1f} {(x2 - 6):.1f},{(y_b_top + 4):.1f}" '
                f'fill="#94a3b8" stroke="none"/>'
            )
    
    html_parts.append('        </g>')
    
    html_parts.append("""      </svg>
    </div>
    
    <div class="panel">
      <h3 style="margin-top: 0;">Job Legend</h3>
      <table>
        <thead>
          <tr><th>Job</th><th>Operations</th><th>Total Time</th></tr>
        </thead>
        <tbody>
""")
    
    # Summary by job
    job_summary: dict[int, dict] = {}
    for op in operations:
        if op.job not in job_summary:
            job_summary[op.job] = {"ops": 0, "pt": 0}
        job_summary[op.job]["ops"] += 1
        job_summary[op.job]["pt"] += op.processing_time
    
    for job in sorted(job_summary.keys()):
        color = _palette(job)
        data = job_summary[job]
        html_parts.append(
            f'          <tr><td><span class="swatch" style="background:{color}"></span>Job {job}</td>'
            f'<td>{data["ops"]}</td><td>{data["pt"]}</td></tr>'
        )
    
    html_parts.append("""        </tbody>
      </table>
    </div>
  </div>
  <script>
    const btn = document.getElementById('toggle-arrows');
    const arrows = document.getElementById('precedence-arrows');
    btn.addEventListener('click', () => {
      const on = arrows.classList.toggle('visible');
      btn.classList.toggle('active', on);
      btn.textContent = on ? 'Hide Precedence' : 'Show Precedence';
    });
  </script>
</body>
</html>""")
    
    return "\n".join(html_parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Visualize JSSP solutions as HTML Gantt charts.  "
            "Accepts: (1) a DSL instance file with @warm_start completion matrix, "
            "or (2) a main.py result text file, or (3) raw result text via --result-text."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dsl-file", help="JSSP OptDSL instance file with @warm_start solution.")
    group.add_argument("--result-file", help="Text file containing main.py / MiniZinc result output.")
    group.add_argument(
        "--result-text",
        help="Raw result output text (alternative to --result-file).",
    )
    parser.add_argument(
        "--instance-file",
        help=(
            "JSSP DSL instance file (required when using --result-file / --result-text). "
            "If omitted, the instance is looked for in the same directory as the result file."
        ),
    )
    parser.add_argument("--output", default="jssp_solution_viz.html", help="Output HTML path.")
    parser.add_argument("--title", default="JSSP Solution", help="Title shown in HTML.")
    args = parser.parse_args()

    # ── 1. Resolve result text ──────────────────────────────────────────────────
    if args.result_text:
        result_text: str = args.result_text
    elif args.result_file:
        result_text = _read_text_with_fallback(args.result_file)
    else:
        # DSL file mode — read the warm_start from the file directly
        result_text = ""

    # ── 2. Resolve instance data ─────────────────────────────────────────────────
    if args.dsl_file:
        # Both instance and solution are in the same DSL file
        dsl_text = _read_text_with_fallback(args.dsl_file)
        try:
            instance = parse_instance_data(dsl_text)
        except ValueError as exc:
            print(f"Error parsing instance data: {exc}")
            raise SystemExit(2) from exc
        try:
            solution = parse_solution_data(dsl_text)
        except ValueError as exc:
            print(f"Error parsing solution: {exc}")
            raise SystemExit(2) from exc
    else:
        # Instance and result come from separate sources
        instance_dsl_path: str | None = args.instance_file
        if not instance_dsl_path and args.result_file:
            # Look next to the result file
            base = os.path.dirname(os.path.abspath(args.result_file))
            candidates = [os.path.join(base, n) for n in os.listdir(base)]
            for c in candidates:
                if os.path.isfile(c) and "jssp" in os.path.basename(c).lower():
                    instance_dsl_path = c
                    break
        if not instance_dsl_path:
            raise SystemExit("Error: --instance-file required when using --result-file / --result-text.")
        dsl_text = _read_text_with_fallback(instance_dsl_path)
        try:
            instance = parse_instance_data(dsl_text)
        except ValueError as exc:
            print(f"Error parsing instance data from {instance_dsl_path}: {exc}")
            raise SystemExit(2) from exc

        if result_text:
            try:
                solution = _parse_result_best_solution(result_text)
            except ValueError as exc:
                print(f"Error parsing result text: {exc}")
                raise SystemExit(2) from exc
        else:
            raise SystemExit("Error: no result text provided.")

    # ── 3. Extract operations ───────────────────────────────────────────────────
    operations = parse_completion_times(
        solution,
        instance["n_jobs"],
        instance["n_machines"],
        instance["machine_sequence"],
    )
    if operations:
        operations = _compute_operation_times(operations, instance["processing_times"])

    # ── 4. Render and write HTML ────────────────────────────────────────────────
    makespan = max((op.end_time for op in operations), default=0)
    html_text = render_gantt_html(
        operations,
        instance,
        f"{args.title}  ·  makespan={makespan}",
    )
    out_path = os.path.abspath(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_text)
    print(f"Wrote visualization to: {out_path}")


def _extract_balanced_bracket(text: str, start: int) -> str:
    """Extract a balanced-bracket list/array from `text` starting at `[` at `start`."""
    if start >= len(text) or text[start] != "[":
        return text[start:]
    depth = 0
    in_str = False
    str_char = None
    i = start
    while i < len(text):
        ch = text[i]
        if not in_str:
            if ch in '"\'':
                in_str = True
                str_char = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        else:
            if ch == "\\" and i + 1 < len(text):
                i += 2
                continue
            elif ch == str_char:
                in_str = False
                str_char = None
        i += 1
    return text[start:i]


def _scan_top_level_dict(text: str) -> Any | None:
    """Find 'completion': [...] at the top level of the MiniZinc result dict.

    The file format is:
        {'best_solution': Solution(...lambda...), 'statistics': {...},
         'objective': 10, 'completion': [[[2,3,4,5,6], ...]]}

    The outer dict is not literal-eval-able due to the lambda in best_solution,
    but we can scan the text for "'completion':" at the top level using a simple
    string search.  We verify it is truly a top-level key by checking that none
    of the outer-dict closing braces appear BEFORE the key (i.e., the key is not
    inside a nested dict that closed before the outer level).
    """
    key_marker = "'completion':"
    pos = text.find(key_marker)
    if pos < 0:
        return None

    # Verify this key is at the top dict level by checking there is no
    # preceding outer-dict close '}' before pos.  If there were a closing brace
    # it would mean we had already exited the outer dict structure.
    # Walk backwards from pos looking for a } at depth 0 — if found, we are in
    # a nested sub-dict.
    i = pos - 1
    in_str = False
    str_char = None
    depth = 0
    while i >= 0:
        ch = text[i]
        if in_str:
            if ch == "\\" and i > 0:
                i -= 2
                continue
            if ch == str_char:
                in_str = False
                str_char = None
            i -= 1
            continue
        if ch in '"\'':
            in_str = True
            str_char = ch
            i -= 1
            continue
        if depth == 0 and ch == "}":
            # Found a top-level close before our key — key is in a nested dict
            return None
        if ch == "}":
            depth += 1
        elif ch == "{":
            depth -= 1
        i -= 1

    # Found 'completion': at top level. Extract the bracketed value.
    val_start = pos + len(key_marker)
    while val_start < len(text) and text[val_start] in " \t":
        val_start += 1
    if val_start >= len(text) or text[val_start] != "[":
        return None

    result = _extract_balanced_bracket(text, val_start)
    try:
        return ast.literal_eval(result)
    except Exception:
        return result


def _extract_completion_from_best_solution(result_text: str) -> Any | None:
    """Extract the completion matrix from the 'best_solution' repr (which may contain
    Python objects like <bound method ...> that are not valid literals).

    The MiniZinc best_solution field is a Python repr string containing the nested
    `Solution(completion=[...])` object with a <bound method> lambda.  This function
    finds 'completion=' inside that repr and extracts the balanced bracket list
    value using bracket-depth counting.
    """
    marker = "best_solution"
    pos = result_text.find(marker)
    if pos < 0:
        return None
    # Find the opening brace of the best_solution dict
    brace = result_text.find("{", pos)
    if brace < 0:
        return None
    """Extract the completion matrix from the 'best_solution' repr (which may contain
    Python objects like <bound method ...> that are not valid literals).
    
    Locates the 'completion=' field inside the 'best_solution' dict and extracts
    the nested list value using bracket-depth counting, bypassing the non-literal
    'check' field entirely.
    """
    marker = "best_solution"
    pos = result_text.find(marker)
    if pos < 0:
        return None
    # Find the opening brace of the best_solution dict
    brace = result_text.find("{", pos)
    if brace < 0:
        return None
    # Walk the dict, tracking string literals, commas, and nested structures
    # to locate the completion= field and extract its value
    depth = 0  # dict brace depth
    in_str = False
    str_char = None
    i = brace
    field_start = -1
    value_start = -1
    # State machine: looking for 'completion' key at depth==1 inside dict
    key_buf = ""
    phase = "search"  # 'search' | 'found_key' | 'found_value'
    value_bracket_depth = 0

    while i < len(result_text):
        ch = result_text[i]
        if in_str:
            if ch == "\\" and i + 1 < len(result_text):
                i += 2
                continue
            elif ch == str_char:
                in_str = False
                str_char = None
            i += 1
            continue

        if phase == "search":
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break  # end of best_solution dict
            elif ch == "=" and depth == 1 and not in_str:
                # potential key= value at the top level of the dict
                candidate_key = key_buf.strip()
                if candidate_key == "completion":
                    phase = "found_key"
                    key_buf = ""
                    i += 1
                    # skip whitespace
                    while i < len(result_text) and result_text[i] in " \t":
                        i += 1
                    if i < len(result_text) and result_text[i] == "[":
                        phase = "found_value"
                        value_start = i
                        value_bracket_depth = 0
                    continue
                key_buf = ""
            else:
                key_buf += ch
        elif phase == "found_key":
            # skipping to reach the value
            if ch not in " \t,":
                if ch == "[":
                    phase = "found_value"
                    value_start = i
                    value_bracket_depth = 0
                else:
                    phase = "search"
                    key_buf = ""
        elif phase == "found_value":
            if ch == "[":
                value_bracket_depth += 1
            elif ch == "]":
                value_bracket_depth -= 1
                if value_bracket_depth == 0:
                    # Extract the list
                    result_str = result_text[value_start : i + 1]
                    try:
                        return ast.literal_eval(result_str)
                    except Exception:
                        return result_str
            elif ch == "{" or ch == "}":
                # Unmatched braces inside the list value (from nested reprs)
                # Treat them as regular characters that won't close our list
                pass
        i += 1

    return None
    """Extract the completion matrix from the 'best_solution' repr (which may contain
    Python objects like <bound method ...> that are not valid literals).
    
    Locates the 'completion=' field inside the 'best_solution' dict and extracts
    the nested list value using bracket-depth counting, bypassing the non-literal
    'check' field entirely.
    """
    marker = "best_solution"
    pos = result_text.find(marker)
    if pos < 0:
        return None
    # Find the opening brace of the best_solution dict
    brace = result_text.find("{", pos)
    if brace < 0:
        return None
    # Walk the dict, tracking string literals, commas, and nested structures
    # to locate the completion= field and extract its value
    depth = 0  # dict brace depth
    in_str = False
    str_char = None
    i = brace
    field_start = -1
    value_start = -1
    # State machine: looking for 'completion' key at depth==1 inside dict
    key_buf = ""
    phase = "search"  # 'search' | 'found_key' | 'found_value'
    value_bracket_depth = 0

    while i < len(result_text):
        ch = result_text[i]
        if in_str:
            if ch == "\\" and i + 1 < len(result_text):
                i += 2
                continue
            elif ch == str_char:
                in_str = False
                str_char = None
            i += 1
            continue

        if ch in '"\'':
            in_str = True
            str_char = ch
            if phase == "search":
                key_buf = ""
            i += 1
            continue

        if phase == "search":
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break  # end of best_solution dict
            elif ch == "=" and depth == 1 and not in_str:
                # potential key= value at the top level of the dict
                candidate_key = key_buf.strip()
                if candidate_key == "completion":
                    phase = "found_key"
                    key_buf = ""
                    i += 1
                    # skip whitespace
                    while i < len(result_text) and result_text[i] in " \t":
                        i += 1
                    if i < len(result_text) and result_text[i] == "[":
                        phase = "found_value"
                        value_start = i
                        value_bracket_depth = 0
                    continue
                key_buf = ""
            else:
                key_buf += ch
        elif phase == "found_key":
            # skipping to reach the value
            if ch not in " \t,":
                if ch == "[":
                    phase = "found_value"
                    value_start = i
                    value_bracket_depth = 0
                else:
                    phase = "search"
                    key_buf = ""
        elif phase == "found_value":
            if ch == "[":
                value_bracket_depth += 1
            elif ch == "]":
                value_bracket_depth -= 1
                if value_bracket_depth == 0:
                    # Extract the list
                    result_str = result_text[value_start : i + 1]
                    try:
                        return ast.literal_eval(result_str)
                    except Exception:
                        return result_str
            elif ch == "{" or ch == "}":
                # Unmatched braces inside the list value (from nested reprs)
                # Treat them as regular characters that won't close our list
                pass
        i += 1

    return None


def _parse_result_best_solution(result_text: str) -> dict[str, Any]:
    """Parse a JSSP solution dict from main.py / MiniZinc raw output text.

    Three formats are supported:
    1. 'Variable assignment (best solution):' block — clean one-value-per-line
       format (used by LNS output path).
    2. Top-level 'completion': [...] in a MiniZinc outer result dict
       (the full result is a Python dict repr that cannot be ast.literal_eval'd
       due to <bound method> fields, but 'completion' is a plain list at depth 1).
    3. completion= inside the best_solution repr (our last resort).
    """
    # 1. Try clean assignment block first
    markers = (
        "Variable assignment (best solution):",
        "Variable assignment (incumbent):",
    )
    for marker in markers:
        marker_pos = result_text.find(marker)
        if marker_pos >= 0:
            lines = result_text[marker_pos + len(marker) :].splitlines()
            data: dict[str, Any] = {}
            for raw_line in lines:
                line = raw_line.strip()
                if not line:
                    if data:
                        break
                    continue
                if " = " not in line:
                    continue
                name, raw_value = line.split(" = ", 1)
                name = name.strip()
                raw_value = raw_value.strip()
                if raw_value in ("<unassigned>",) or raw_value.startswith("<bound"):
                    continue
                try:
                    data[name] = ast.literal_eval(raw_value)
                except (ValueError, SyntaxError):
                    data[name] = raw_value
            if "completion" in data:
                return data

    # 2. Scan the outer result dict (which may have <bound method> fields)
    # for 'completion': [...] at dict nesting depth 1.
    completion = _scan_top_level_dict(result_text)
    if completion is not None and len(completion) == 1:
        # The MiniZinc outer dict wraps the completion in an extra list.
        # 'completion': [[[job0-op-times], [job1-op-times], ...]]
        # should be: [[job0-op-times], [job1-op-times], ...]
        inner = completion[0]
        if isinstance(inner, list) and all(isinstance(row, list) for row in inner):
            completion = inner
    if completion is not None:
        return {"completion": completion}

    # 3. Fall back to extraction inside the best_solution repr
    completion = _extract_completion_from_best_solution(result_text)
    if completion is not None:
        return {"completion": completion}

    raise ValueError(
        "Could not find 'completion' in 'Variable assignment' block, "
        "top-level dict, or 'best_solution' repr in result text."
    )


if __name__ == "__main__":
    main()