from src.core.application_backup import decode_application_backup, encrypt_application_backup


def test_application_backup_round_trip():
    backup = {
        "format": "archive-deployment-backup",
        "format_version": 3,
        "fernet_keys": ["gAAAAABplaceholder"],
        "options": {"include_users": False},
    }
    # The archive decoder validates Fernet keys separately; this test focuses on
    # the password envelope, so use the encryption function and replace the
    # metadata with a valid Fernet key in a real archive-shaped payload.
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    backup["fernet_keys"] = [key, key]
    encoded = encrypt_application_backup(backup, "a-valid-backup-password")
    assert decode_application_backup(encoded, "a-valid-backup-password") == backup


def test_application_backup_preview_includes_smtp_when_present():
    from cryptography.fernet import Fernet
    from src.core.application_backup import encrypt_application_backup, preview_application_backup

    key = Fernet.generate_key().decode()
    smtp_password = Fernet(key.encode()).encrypt(b"smtp-secret").decode()
    backup = {
        "format": "archive-deployment-backup",
        "format_version": 3,
        "secret_values_encrypted": True,
        "fernet_keys": [key, key],
        "options": {"include_smtp_settings": True},
        "app_integration_settings": {
            "smtp_enabled": True,
            "smtp_host": "mail.example.test",
            "smtp_port": 587,
            "smtp_password": smtp_password,
            "smtp_from_email": "archive@example.test",
        },
        "oidc_settings": {},
    }
    encoded = encrypt_application_backup(backup, "a-valid-backup-password")
    preview = preview_application_backup(encoded, "a-valid-backup-password")
    assert preview["smtp"]["smtp_enabled"] is True
    assert preview["smtp"]["smtp_host"] == "mail.example.test"
    assert preview["smtp"]["smtp_password"] == "smtp-secret"
