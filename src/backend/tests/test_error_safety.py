from fastapi.exceptions import RequestValidationError

from src.main import _safe_validation_errors


def test_validation_errors_do_not_echo_submitted_secret() -> None:
    secret = "SuperSecret123!"
    exc = RequestValidationError(
        [
            {
                "type": "value_error",
                "loc": ("body", "new_password"),
                "msg": "Value error, Password must contain an uppercase letter.",
                "input": secret,
                "ctx": {"error": ValueError("Password must contain an uppercase letter.")},
            }
        ]
    )

    errors = _safe_validation_errors(exc)

    assert secret not in str(errors)
    assert "input" not in errors[0]
    assert "ctx" not in errors[0]
    assert "Password must contain an uppercase letter." in errors[0]["msg"]
