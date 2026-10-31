from app.core.security import hash_password, hash_token, new_token, verify_password


def test_password_is_not_stored_as_plain_text() -> None:
    password_hash = hash_password("секретный-пароль")

    assert "секретный-пароль" not in password_hash
    assert verify_password(password_hash, "секретный-пароль")


def test_wrong_password_is_rejected() -> None:
    password_hash = hash_password("секретный-пароль")

    assert not verify_password(password_hash, "другой-пароль")


def test_broken_hash_is_rejected_without_crashing() -> None:
    assert not verify_password("not-a-hash", "секретный-пароль")


def test_tokens_are_random_and_hashed_deterministically() -> None:
    first, second = new_token(), new_token()

    assert first != second
    assert hash_token(first) == hash_token(first)
    assert hash_token(first) != first
