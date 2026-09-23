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
