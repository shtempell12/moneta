"""H-DEV2: does Moneta read statements of different banks without manual column setup?

Every file in a folder goes through the same steps as an upload in the service:
read the table → guess the columns → parse the rows. Files are named «<bank>_<anything>»,
e.g. «sber_2026-10.csv», so the report can be grouped by bank.

Usage:
    uv run python -m research.statements_check data/statements
"""

import csv
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from app.domain.statement import (
    ColumnMapping,
    StatementFormatError,
    guess_columns,
    parse_rows,
    read_table,
)

REPORT = Path("data/reports/h_dev2_statements.csv")
# Threshold from the hypothesis card: ≥ 99% of rows parsed without errors.
MIN_PARSED_SHARE = 0.99


@dataclass(frozen=True)
class FileResult:
    file: str
    bank: str
    columns_found: bool
    rows: int
    errors: int
    # Statements are mostly expenses; mostly positive amounts mean the sign was lost.
    expense_share: float
    problem: str

    @property
    def parsed_share(self) -> float:
        total = self.rows + self.errors
        return self.rows / total if total else 0.0

    @property
    def loaded_without_setup(self) -> bool:
        """The H-DEV2 success criterion for one file."""
        return (
            self.columns_found
            and self.parsed_share >= MIN_PARSED_SHARE
            and self.expense_share >= 0.5
        )


def check_file(path: Path) -> FileResult:
    bank = path.stem.split("_")[0].lower()
    try:
        table = read_table(path.read_bytes(), path.name)
    except StatementFormatError as error:
        return FileResult(path.name, bank, False, 0, 0, 0.0, str(error))

    guess = guess_columns(list(table.columns))
    if not (guess["date"] and guess["amount"] and guess["description"]):
        missing = [field for field in ("date", "amount", "description") if not guess[field]]
        return FileResult(path.name, bank, False, 0, 0, 0.0, f"не найдены: {', '.join(missing)}")

    parsed = parse_rows(
        table,
        ColumnMapping(
            date=guess["date"],
            amount=guess["amount"],
            description=guess["description"],
            bank_category=guess["bank_category"],
        ),
    )
    expenses = sum(row.amount < 0 for row in parsed.rows)
    first_error = parsed.errors[0].message if parsed.errors else ""
    return FileResult(
        file=path.name,
        bank=bank,
        columns_found=True,
        rows=len(parsed.rows),
        errors=len(parsed.errors),
        expense_share=expenses / len(parsed.rows) if parsed.rows else 0.0,
        problem=first_error,
    )


def check_folder(folder: Path) -> list[FileResult]:
    files = sorted(
        path for path in folder.iterdir() if path.is_file() and not path.name.startswith(".")
    )
    return [check_file(path) for path in files]


def main(argv: Sequence[str]) -> None:
    folder = Path(argv[0]) if argv else Path("data/statements")
    results = check_folder(folder)
    if not results:
        print(f"В папке {folder} нет файлов")
        return

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=[*asdict(results[0]), "parsed_share", "loaded_without_setup"]
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    **asdict(result),
                    "parsed_share": round(result.parsed_share, 4),
                    "loaded_without_setup": result.loaded_without_setup,
                }
            )

    by_bank: dict[str, list[FileResult]] = defaultdict(list)
    for result in results:
        by_bank[result.bank].append(result)
    print(f"{'банк':<12}{'файлов':>8}{'без настройки':>16}{'строк без ошибок':>19}")
    for bank, bank_results in sorted(by_bank.items()):
        ok = sum(result.loaded_without_setup for result in bank_results)
        rows = sum(result.rows for result in bank_results)
        total = rows + sum(result.errors for result in bank_results)
        share = f"{rows / total:.1%}" if total else "—"
        print(f"{bank:<12}{len(bank_results):>8}{ok:>16}{share:>19}")
    loaded = sum(result.loaded_without_setup for result in results)
    share_loaded = loaded / len(results)
    print(f"\nИтого: {loaded} из {len(results)} файлов без настройки ({share_loaded:.0%})")
    print(f"Подробно по файлам: {REPORT}")


if __name__ == "__main__":
    main(sys.argv[1:])
