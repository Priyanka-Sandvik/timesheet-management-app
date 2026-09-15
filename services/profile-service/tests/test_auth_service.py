import shutil
import tempfile

import pytest
from py_common.core.errors import AppError
from py_common.core.jwt_issue import JwtIssuer, LocalFileKeySource

from app.models.schemas import RegisterRequest
from app.services.auth_service import AuthService
from tests.fakes import FakeUserRepository


@pytest.fixture
def jwt_issuer():
    tmp_dir = tempfile.mkdtemp()
    try:
        yield JwtIssuer(key_source=LocalFileKeySource(tmp_dir), expiry_hours=8, issuer="profile-service")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def auth_service(jwt_issuer):
    return AuthService(
        repository=FakeUserRepository(),
        jwt_issuer=jwt_issuer,
        allowed_email_domain="sandvik.com",
        admin_emails={"admin1@sandvik.com", "admin2@sandvik.com"},
    )


def _register(auth_service, email="employee1@sandvik.com", full_name="Employee One", password="P@ssw0rd123"):
    return auth_service.register(RegisterRequest(email=email, fullName=full_name, password=password))


def test_register_success(auth_service):
    user = _register(auth_service)
    assert user.email == "employee1@sandvik.com"
    assert user.full_name == "Employee One"
    assert user.password_hash != "P@ssw0rd123"


def test_register_rejects_wrong_domain(auth_service):
    with pytest.raises(AppError) as exc_info:
        auth_service.register(RegisterRequest(email="someone@othercorp.com", fullName="X", password="P@ssw0rd123"))
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "VALIDATION_ERROR"


def test_register_duplicate_email_returns_409(auth_service):
    _register(auth_service)
    with pytest.raises(AppError) as exc_info:
        _register(auth_service)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "CONFLICT"


def test_register_is_case_insensitive_for_duplicates(auth_service):
    _register(auth_service, email="Employee1@Sandvik.com")
    with pytest.raises(AppError) as exc_info:
        _register(auth_service, email="employee1@sandvik.com")
    assert exc_info.value.status_code == 409


def test_login_success_returns_token(auth_service):
    _register(auth_service)
    token, expires_in = auth_service.login("employee1@sandvik.com", "P@ssw0rd123")
    assert isinstance(token, str) and token.count(".") == 2
    assert expires_in == 8 * 3600


def test_login_bad_password_returns_401(auth_service):
    _register(auth_service)
    with pytest.raises(AppError) as exc_info:
        auth_service.login("employee1@sandvik.com", "wrong-password")
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"


def test_login_unknown_email_returns_401(auth_service):
    with pytest.raises(AppError) as exc_info:
        auth_service.login("nobody@sandvik.com", "whatever123")
    assert exc_info.value.status_code == 401


def test_login_deactivated_user_returns_401(auth_service):
    # See ASSUMPTION 1 in app/services/auth_service.py: this service blocks login for
    # deactivated users.
    user = _register(auth_service)
    auth_service._repository.update_active_status(user.email, False)
    with pytest.raises(AppError) as exc_info:
        auth_service.login("employee1@sandvik.com", "P@ssw0rd123")
    assert exc_info.value.status_code == 401


def test_login_embeds_is_admin_true_for_admin_email(auth_service):
    _register(auth_service, email="admin1@sandvik.com", full_name="Admin One")
    token, _ = auth_service.login("admin1@sandvik.com", "P@ssw0rd123")
    import jwt as pyjwt

    public_key_pem = auth_service._jwt_issuer._key_source.get_public_key_pem()
    claims = pyjwt.decode(token, public_key_pem, algorithms=["RS256"], issuer="profile-service")
    assert claims["isAdmin"] is True


def test_login_embeds_is_admin_false_for_regular_email(auth_service):
    _register(auth_service)
    token, _ = auth_service.login("employee1@sandvik.com", "P@ssw0rd123")
    import jwt as pyjwt

    public_key_pem = auth_service._jwt_issuer._key_source.get_public_key_pem()
    claims = pyjwt.decode(token, public_key_pem, algorithms=["RS256"], issuer="profile-service")
    assert claims["isAdmin"] is False


def test_login_as_admin_success(auth_service):
    _register(auth_service, email="admin1@sandvik.com", full_name="Admin One")
    token, _ = auth_service.login_as_admin("admin1@sandvik.com", "P@ssw0rd123")
    assert isinstance(token, str)


def test_login_as_admin_bad_password_returns_401_not_403(auth_service):
    _register(auth_service, email="admin1@sandvik.com", full_name="Admin One")
    with pytest.raises(AppError) as exc_info:
        auth_service.login_as_admin("admin1@sandvik.com", "wrong-password")
    assert exc_info.value.status_code == 401


def test_login_as_admin_non_admin_returns_403_after_password_ok(auth_service):
    _register(auth_service)  # employee1@sandvik.com, not an admin
    with pytest.raises(AppError) as exc_info:
        auth_service.login_as_admin("employee1@sandvik.com", "P@ssw0rd123")
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_is_admin_case_insensitive(auth_service):
    assert auth_service.is_admin("Admin1@Sandvik.com") is True
    assert auth_service.is_admin("nobody@sandvik.com") is False
