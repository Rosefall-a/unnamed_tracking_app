from src.core.auth import create_api_key, hash_password, hash_token, validate_password, verify_password


def test_validate_password_accepts_password_meeting_policy() -> None:
    password = "Correct!9"

    assert validate_password(password) == password


def test_validate_password_rejects_missing_requirements() -> None:
    invalid_passwords = (
        "short!A1",
        "lowercase!1",
        "UPPERCASE!1",
        "NoSymbol99",
    )

    for password in invalid_passwords:
        try:
            validate_password(password)
        except ValueError:
            continue
        raise AssertionError(f"Expected password to be rejected: {password}")


def test_password_hash_round_trip_and_wrong_password() -> None:
    password = "Correct!9"
    stored_hash = hash_password(password)

    assert stored_hash.startswith("scrypt$")
    assert verify_password(password, stored_hash)
    assert not verify_password("Wrong!9", stored_hash)


def test_verify_password_rejects_malformed_hash() -> None:
    assert not verify_password("Correct!9", "not-a-valid-hash")
    assert not verify_password("Correct!9", "bcrypt$1$2$3$00$00")


def test_api_key_contains_only_safe_persisted_derivatives() -> None:
    api_key, prefix, key_hash = create_api_key()

    assert api_key.startswith("utk_")
    assert prefix == api_key[:12]
    assert key_hash == hash_token(api_key)
    assert len(key_hash) == 64
