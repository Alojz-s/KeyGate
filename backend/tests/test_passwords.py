from app.services.passwords import hash_password, verify_password

PASSWORD = "długie-hasło-testowe-bez-roku"


def test_hash_is_argon2id_and_not_plaintext() -> None:
    password_hash = hash_password(PASSWORD)

    assert password_hash != PASSWORD
    assert PASSWORD not in password_hash
    assert password_hash.startswith("$argon2id$")


def test_verify_correct_password() -> None:
    assert verify_password(PASSWORD, hash_password(PASSWORD)) is True


def test_verify_wrong_password() -> None:
    assert verify_password("inne-długie-hasło-testowe", hash_password(PASSWORD)) is False


def test_same_password_gives_different_hashes() -> None:
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)

    assert first != second
    assert verify_password(PASSWORD, first)
    assert verify_password(PASSWORD, second)


def test_verify_invalid_hash_returns_false() -> None:
    assert verify_password(PASSWORD, "to-nie-jest-hash") is False
