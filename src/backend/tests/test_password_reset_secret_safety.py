from fastapi.exceptions import RequestValidationError

from src.main import _safe_validation_errors


def test_password_reset_validation_does_not_echo_password() -> None:
    secret = "ResetSecret123!"
    exc = RequestValidationError(
        [
            {
                "type": "value_error",
                "loc": ("body", "password"),
                "msg": "Value error, invalid password",
                "input": secret,
                "ctx": {"error": ValueError(secret)},
            }
        ]
    )

    errors = _safe_validation_errors(exc)
    assert secret not in str(errors)
    assert "input" not in errors[0]
    assert "ctx" not in errors[0]
