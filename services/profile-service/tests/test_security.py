from app.core.security import hash_password, verify_password


def test_hash_password_produces_argon2id_hash():
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("$argon2id$")


def test_verify_password_roundtrip_success():
    hashed = hash_password("s3cret-Password!")
    assert verify_password("s3cret-Password!", hashed) is True


def test_verify_password_roundtrip_failure():
    hashed = hash_password("s3cret-Password!")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_with_garbage_hash_returns_false():
    assert verify_password("anything", "not-a-real-hash") is False
