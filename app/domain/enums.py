from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class CategoryKind(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class CategorySource(StrEnum):
    """Where a transaction's category came from — the basis of the "manual fixes" metric."""

    BANK = "bank"
    HISTORY = "history"
    MANUAL = "manual"
