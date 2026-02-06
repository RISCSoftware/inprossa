import matplotlib.pyplot as plt
from pathlib import Path


class InstanceProgress:
    """
    Stores solution-improvement progress for ONE instance across MANY solvers.

    Assumption per solver:
      - times are added in increasing order
      - objectives are added in decreasing order (minimization; lower is better)
    """

    def __init__(self, instance_id: str, problem_info=None):
        self.instance_id = instance_id
        self.problem_info = problem_info or {}
        self._data = {}  # solver -> {"times":[], "objectives":[], "end_time":..., "proof_time":..., "status":...}

    def add(self, solver: str, result) -> None:
        self._data[solver] = result

    def get_timings(self, solver: str) -> list[float]:
        return self._data[solver]["total_time"]

    def plot(
        self,
        print_figures: bool = False,
        *,
        outfile=None,
        logx=False,
        extend_to_global_end=True,
        title=None,
        point_size=80,            # "thick point"
        line_width=2.0,
        proof_tick_width=6.0,     # "thick short vertical line"
        proof_tick_frac=0.06      # tick height as fraction of y-range
    ):
        """
        - Step line per solver (single color per solver).
        - A thick point at every improvement (same color).
        - If proof_time exists: draw a short thick vertical tick at proof_time (same color)
          and STOP the curve at proof_time.
        """
        if not self._data:
            raise ValueError("No solver data to plot")

        # global end for fair comparison (only used when NOT proven optimal)
        end_times = [r["total_time"] for r in self._data.values()]
        global_end = max(end_times) if end_times else None

        fig, ax = plt.subplots(figsize=(10, 6))

        # deterministic color list (matplotlib cycle)
        palette = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])
        solvers = list(self._data.keys())

        # store proof markers to draw after y-limits are known: (pt, y_at_pt, color)
        proof_marks = []

        for i, solver in enumerate(solvers):
            run = self._data[solver]
            times = run["times"]
            objs = run["objectives"]
            proof_time = run["end_time"] if run["status"] == "OPTIMAL SOLUTION" else None
            color = palette[i % len(palette)] if palette else None

            if not times:
                ax.plot([], [], label=f"{solver} (no solution)")
                continue

            # ---- STOP at proof_time (if provided) ----
            plot_times = times
            plot_objs = objs
            if proof_time is not None:
                # keep points with t <= proof_time
                k = 0
                while k < len(plot_times) and plot_times[k] <= proof_time:
                    k += 1
                plot_times = plot_times[:k]
                plot_objs = plot_objs[:k]

                if plot_times:
                    # extend flat to proof_time if last point is earlier
                    if plot_times[-1] < proof_time:
                        plot_times = plot_times + [proof_time]
                        plot_objs = plot_objs + [plot_objs[-1]]

                    # remember where to draw the proof tick (at the objective value at proof)
                    proof_marks.append((proof_time, plot_objs[-1], color))
                else:
                    # no solution before proof_time; just ignore proof marker
                    pass

            # step curve
            ax.step(plot_times, plot_objs, where="post", label=solver, linewidth=line_width, color=color)

            # thick points at *improvements* (use original points, but clipped if proven optimal)
            point_times = times
            point_objs = objs
            if proof_time is not None:
                clipped = [(t, o) for t, o in zip(times, objs) if t <= proof_time]
                point_times = [t for t, _ in clipped]
                point_objs = [o for _, o in clipped]

            ax.scatter(point_times, point_objs, s=point_size, color=color, zorder=3)

            # extend flat line to global end ONLY if not proven optimal
            if proof_time is None and extend_to_global_end and global_end is not None and plot_times[-1] < global_end:
                ax.step([plot_times[-1], global_end], [plot_objs[-1], plot_objs[-1]],
                        where="post", linewidth=line_width, color=color)

        # labels / style
        ax.set_xlabel("Time since start (s)")
        ax.set_ylabel("Objective (lower is better)")
        ax.grid(True, which="both")
        if logx:
            ax.set_xscale("log")

        if title is None:
            title = f"Objective improvement over time — {self.instance_id}"
        ax.set_title(title)
        ax.legend()

        # set x-limits after plotting
        if global_end is not None:
            ax.set_xlim(left=0, right=(global_end * 1.02 if global_end > 0 else 1.0))

        # autoscale then draw proof ticks (short + thick, same color) and keep them short
        ax.relim()
        ax.autoscale_view()
        y0, y1 = ax.get_ylim()
        tick_len = max(1e-12, (y1 - y0) * proof_tick_frac)

        for pt, y_at_pt, color in proof_marks:
            ax.vlines(pt, y_at_pt - tick_len / 2, y_at_pt + tick_len / 2,
                      colors=color, linewidth=proof_tick_width, zorder=4)

        fig.tight_layout()
        if outfile:
            out_file = Path(outfile)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(outfile, dpi=200)
        if print_figures:
            return fig, ax
    