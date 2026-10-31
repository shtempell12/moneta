from app.domain.enums import CategoryKind

MIN_PASSWORD_LENGTH = 8
MAX_EMAIL_LENGTH = 255

DEFAULT_CATEGORIES: dict[CategoryKind, tuple[str, ...]] = {
    CategoryKind.EXPENSE: (
        "Продукты",
        "Кафе и рестораны",
        "Транспорт",
        "Дом и ЖКХ",
        "Связь и интернет",
        "Здоровье",
        "Красота",
        "Дети",
        "Одежда",
        "Развлечения",
        "Подарки",
        "Другое",
    ),
    CategoryKind.INCOME: ("Зарплата", "Прочие доходы"),
}


def normalize_email(email: str) -> str:
    """Make emails comparable: «Anna@Mail.ru » and «anna@mail.ru» are the same user."""
    return email.strip().lower()


def email_problem(email: str) -> str | None:
    """Return a user-facing reason why the email is invalid, or None if it looks fine."""
    local, _, domain = email.partition("@")
    if not local or "." not in domain or len(email) > MAX_EMAIL_LENGTH:
        return "Проверьте email: похоже, в нём ошибка"
    return None


def password_problem(password: str) -> str | None:
    """Return a user-facing reason why the password is too weak, or None if it is fine."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов"
    return None
