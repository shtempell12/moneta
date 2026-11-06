"""Run the H-ML1 comparison and save the tables.

Usage:
    uv run python -m research.evaluate                       # synthetic data, checks the code
    uv run python -m research.evaluate data/labeled.csv      # real anonymized data

Results go to data/reports/ (git-ignored, as they come from users' data).
"""

import csv
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from research.dataset import read_dataset
from research.evaluation import UserResult, evaluate, summarize
from research.synthetic import generate

REPORTS = Path("data/reports")
HISTORY_DAYS = [14, 30, 60, None]


def main(argv: Sequence[str]) -> None:
    rows = read_dataset(Path(argv[0])) if argv else generate()
    source = Path(argv[0]).stem if argv else "synthetic"
    REPORTS.mkdir(parents=True, exist_ok=True)

    per_user = evaluate(rows)
    _write(REPORTS / f"h_ml1_{source}_per_user.csv", [asdict(row) for row in per_user])
    print(f"Пользователей: {len({row.user for row in rows})}, операций: {len(rows)}\n")
    _print_summary("Вся история", per_user)

    curve = []
    for days in HISTORY_DAYS:
        for summary in summarize(evaluate(rows, history_days=days)):
            curve.append({"history_days": days or "all", **asdict(summary)})
    _write(REPORTS / f"h_ml1_{source}_history.csv", curve)
    print(f"\nТаблицы сохранены в {REPORTS}/")


def _print_summary(title: str, results: Sequence[UserResult]) -> None:
    print(f"{title}:")
    print(f"{'подход':<15}{'точность':>10}{'польз. ≥70%':>14}{'смешанные':>12}")
    for summary in summarize(results):
        mixed = f"{summary.mixed_accuracy:.0%}" if summary.mixed_accuracy is not None else "—"
        print(
            f"{summary.approach:<15}{summary.accuracy:>10.0%}"
            f"{summary.users_at_70:>14.0%}{mixed:>12}"
        )


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1:])
