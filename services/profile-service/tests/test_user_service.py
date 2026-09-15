import pytest
from py_common.core.errors import AppError

from app.services.user_service import UserService
from tests.fakes import FakeUserRepository


@pytest.fixture
def repo():
    repo = FakeUserRepository()
    repo.create(email="employee1@sandvik.com", full_name="Employee One", password_hash="hash")
    repo.create(email="admin1@sandvik.com", full_name="Admin One", password_hash="hash")
    return repo


@pytest.fixture
def user_service(repo):
    return UserService(repository=repo, admin_emails={"admin1@sandvik.com"})


def test_get_me_returns_expected_fields(user_service):
    me = user_service.get_me("employee1@sandvik.com")
    assert me.email == "employee1@sandvik.com"
    assert me.fullName == "Employee One"
    assert me.isAdmin is False
    assert me.isActive is True


def test_get_me_admin_flag(user_service):
    me = user_service.get_me("admin1@sandvik.com")
    assert me.isAdmin is True


def test_get_me_unknown_user_404(user_service):
    with pytest.raises(AppError) as exc_info:
        user_service.get_me("nobody@sandvik.com")
    assert exc_info.value.status_code == 404


def test_set_user_status_deactivates(user_service):
    updated = user_service.set_user_status("employee1@sandvik.com", False)
    assert updated.is_active is False


def test_set_user_status_unknown_user_404(user_service):
    with pytest.raises(AppError) as exc_info:
        user_service.set_user_status("nobody@sandvik.com", False)
    assert exc_info.value.status_code == 404


def test_list_users_active_only(user_service):
    user_service.set_user_status("employee1@sandvik.com", False)
    all_users = user_service.list_users(active_only=False)
    active_users = user_service.list_users(active_only=True)
    assert len(all_users) == 2
    assert len(active_users) == 1
    assert active_users[0].email == "admin1@sandvik.com"
