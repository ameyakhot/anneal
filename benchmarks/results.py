"""Accumulate and display benchmark results."""

from __future__ import annotations


class ResultsAccumulator:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def add(self, task_id: str, method: str, scores: dict) -> None:
        self.records.append({"task_id": task_id, "method": method, **scores})

    def print_summary(self) -> None:
        if not self.records:
            print("No results.")
            return

        methods = sorted(set(r["method"] for r in self.records))
        tasks = sorted(set(r["task_id"] for r in self.records))

        # Per-method averages
        print(f"\n{'=' * 80}")
        print(f"BENCHMARK RESULTS ({len(tasks)} tasks)")
        print(f"{'=' * 80}")

        header = f"{'Method':<20} {'Recall':>8} {'Precision':>10} {'F1':>8} {'Util%':>8} {'Perfect':>8}"
        print(header)
        print("-" * len(header))

        for method in methods:
            method_records = [r for r in self.records if r["method"] == method]
            avg_recall = sum(r["recall"] for r in method_records) / len(method_records)
            avg_precision = sum(r["precision"] for r in method_records) / len(method_records)
            avg_f1 = sum(r["f1"] for r in method_records) / len(method_records)
            avg_util = sum(r["utilization"] for r in method_records) / len(method_records)
            perfect = sum(1 for r in method_records if r["recall"] == 1.0)

            print(f"{method:<20} {avg_recall:>7.1%} {avg_precision:>9.1%} "
                  f"{avg_f1:>7.1%} {avg_util:>7.1%} {perfect:>5}/{len(method_records)}")

        print(f"{'=' * 80}")

        # Per-task detail (show misses)
        print(f"\nPER-TASK DETAIL (missing files)")
        print("-" * 80)
        for task_id in tasks:
            task_records = [r for r in self.records if r["task_id"] == task_id]
            for r in task_records:
                if r["missing"]:
                    missing_str = ", ".join(r["missing"])
                    print(f"  {task_id} [{r['method']}]: missing {missing_str}")

        print()
