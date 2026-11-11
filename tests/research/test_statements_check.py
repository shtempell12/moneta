from pathlib import Path

from research.statements_check import check_file, check_folder

TBANK_LIKE = "\n".join(
    [
        "Дата операции;Сумма платежа;Категория;Описание",
        "03.10.2026 10:00:00;-1 500,00;Супермаркеты;ПЯТЕРОЧКА",
        "04.10.2026 12:00:00;-63,00;Транспорт;Метро",
        "15.10.2026 09:00:00;+85 000,00;Пополнения;Зарплата",
    ]
)


def write(folder: Path, name: str, text: str, encoding: str = "cp1251") -> Path:
    path = folder / name
    path.write_bytes(text.encode(encoding))
    return path


def test_statement_with_known_columns_loads_without_setup(tmp_path: Path) -> None:
    result = check_file(write(tmp_path, "tbank_october.csv", TBANK_LIKE))

    assert result.bank == "tbank"
    assert (result.columns_found, result.rows, result.errors) == (True, 3, 0)
    assert result.loaded_without_setup


def test_unknown_column_names_need_manual_setup(tmp_path: Path) -> None:
    text = "Date;Amount;Details\n03.10.2026;-100;Shop\n04.10.2026;-200;Cafe"

    result = check_file(write(tmp_path, "foreign_bank.csv", text, "utf-8"))

    assert not result.loaded_without_setup
    assert "не найдены" in result.problem or "Не нашли" in result.problem


def test_lost_minus_sign_is_flagged(tmp_path: Path) -> None:
    result = check_file(write(tmp_path, "bank_plus.csv", TBANK_LIKE.replace("-", "")))

    assert result.expense_share == 0
    assert not result.loaded_without_setup


def test_broken_rows_are_counted(tmp_path: Path) -> None:
    text = TBANK_LIKE + "\n05.10.2026;сто рублей;Кафе;Кофемания"

    result = check_file(write(tmp_path, "sber_broken.csv", text))

    assert (result.rows, result.errors) == (3, 1)
    assert not result.loaded_without_setup


def test_broken_file_is_reported_not_crashed(tmp_path: Path) -> None:
    (tmp_path / "vtb_statement.pdf").write_bytes(b"%PDF-1.4")

    [result] = check_folder(tmp_path)

    assert not result.columns_found
    assert "PDF" in result.problem
