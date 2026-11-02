from datetime import date, timedelta

import pytest
from py_common.core.errors import AppError

from app.models.schemas import CreateUserRequest, UpdateUserRequest
from app.models.user import UserDetails
from app.services.user_import import parse_csv
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
    return UserService(repository=repo, admin_emails={"admin1@sandvik.com"}, allowed_email_domain="sandvik.com")


def _yesterday() -> date:
    return date.today() - timedelta(days=1)


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


def test_is_active_is_derived_from_end_date(user_service, repo):
    repo.update_profile("employee1@sandvik.com", "Employee One", UserDetails(end_date=_yesterday()))
    repo.update_profile("admin1@sandvik.com", "Admin One", UserDetails(end_date=date.today()))

    by_email = {u.email: u for u in user_service.list_users()}
    assert by_email["employee1@sandvik.com"].isActive is False
    assert by_email["admin1@sandvik.com"].isActive is True  # active through the end date itself
    assert user_service.get_me("employee1@sandvik.com").isActive is False


def test_list_users_active_only(user_service, repo):
    repo.update_profile("employee1@sandvik.com", "Employee One", UserDetails(end_date=_yesterday()))
    all_users = user_service.list_users(active_only=False)
    active_users = user_service.list_users(active_only=True)
    assert len(all_users) == 2
    assert len(active_users) == 1
    assert active_users[0].email == "admin1@sandvik.com"


def test_create_user_with_only_name_and_email(user_service):
    created = user_service.create_user(CreateUserRequest(fullName="  New Person ", email="New.Person@sandvik.com"))
    assert created.email == "new.person@sandvik.com"
    assert created.fullName == "New Person"
    assert created.vendor is None and created.vendorRate is None
    assert created.isActive is True


def test_create_user_saves_all_details(user_service):
    created = user_service.create_user(
        CreateUserRequest(
            fullName="Vendor Person",
            email="vendor.person@sandvik.com",
            startDate="2026-01-01",
            endDate="2026-12-31",
            vendor="Acme",
            vendorEmail="contact@acme.com",
            vendorPhone="+46 1",
            vendorRate=80,
            sandvikRate=95.5,
        )
    )
    assert (created.vendor, created.vendorEmail, created.vendorPhone) == ("Acme", "contact@acme.com", "+46 1")
    assert (created.vendorRate, created.sandvikRate) == (80.0, 95.5)
    assert created.startDate == date(2026, 1, 1) and created.endDate == date(2026, 12, 31)


def test_create_user_duplicate_email_409(user_service):
    with pytest.raises(AppError) as exc_info:
        user_service.create_user(CreateUserRequest(fullName="Dup", email="Employee1@sandvik.com"))
    assert exc_info.value.status_code == 409


def test_create_user_wrong_domain_400(user_service):
    with pytest.raises(AppError) as exc_info:
        user_service.create_user(CreateUserRequest(fullName="X", email="x@othercorp.com"))
    assert exc_info.value.status_code == 400


def test_request_rejects_end_before_start_and_negative_rate():
    with pytest.raises(ValueError):
        CreateUserRequest(fullName="X", email="x@sandvik.com", startDate="2026-05-01", endDate="2026-04-01")
    with pytest.raises(ValueError):
        CreateUserRequest(fullName="X", email="x@sandvik.com", vendorRate=-1)


def test_update_user_replaces_details_and_clears_blanks(user_service):
    user_service.create_user(CreateUserRequest(fullName="Edit Me", email="edit.me@sandvik.com", vendor="Old", vendorRate=10))
    updated = user_service.update_user(
        "edit.me@sandvik.com", UpdateUserRequest(fullName="Edited", vendor="  ", sandvikRate=20, endDate="2026-06-30")
    )
    assert updated.fullName == "Edited"
    assert updated.vendor is None and updated.vendorRate is None
    assert updated.sandvikRate == 20.0 and updated.endDate == date(2026, 6, 30)


def test_update_user_unknown_404(user_service):
    with pytest.raises(AppError) as exc_info:
        user_service.update_user("nobody@sandvik.com", UpdateUserRequest(fullName="X"))
    assert exc_info.value.status_code == 404


# ---------- import ----------


def test_import_creates_updates_and_reports_errors(user_service):
    user_service.create_user(
        CreateUserRequest(fullName="Employee Two", email="employee2@sandvik.com", vendor="Keep Me", vendorRate=50)
    )
    csv_text = (
        "Name,Email,Start Date,End Date,Vendor,Vendor Rate,Sandvik Rate\n"
        "New One,new1@sandvik.com,2026-01-01,2026-12-31,Acme,80,95\n"
        "New Two,new2@sandvik.com,,,,,\n"  # only the mandatory values
        "Employee Two Renamed,employee2@sandvik.com,,2026-09-30,,,120\n"  # update; blanks keep old values
        ",noname@sandvik.com,,,,,\n"
        "Bad Email,not-an-email,,,,,\n"
        "Bad Date,baddate@sandvik.com,31st Jan,,,,\n"
        "Backwards,back@sandvik.com,2026-05-01,2026-04-01,,,\n"
        "Bad Rate,badrate@sandvik.com,,,,abc,\n"
        "Negative,neg@sandvik.com,,,,-5,\n"
        "Dup,new1@sandvik.com,,,,,\n"
    )

    result = user_service.import_users(parse_csv(csv_text.encode()))

    assert (result.created, result.updated) == (2, 1)
    assert [e.row for e in result.errors] == [5, 6, 7, 8, 9, 10, 11]
    by_email = {u.email: u for u in user_service.list_users()}
    assert by_email["new1@sandvik.com"].vendorRate == 80.0
    assert by_email["new2@sandvik.com"].vendor is None
    renamed = by_email["employee2@sandvik.com"]
    assert renamed.fullName == "Employee Two Renamed"
    assert renamed.vendor == "Keep Me" and renamed.vendorRate == 50.0  # blank cells left untouched
    assert renamed.sandvikRate == 120.0 and renamed.endDate == date(2026, 9, 30)


def test_import_with_only_required_columns(user_service):
    result = user_service.import_users(parse_csv(b"Name,Email\nA B,a.b@sandvik.com\n"))
    assert (result.created, result.updated, result.errors) == (1, 0, [])


def test_import_missing_required_column_fails_whole_file():
    with pytest.raises(AppError) as exc_info:
        parse_csv(b"Name,Vendor\nA B,Acme\n")
    assert exc_info.value.status_code == 400


def test_import_update_that_would_put_end_before_existing_start_is_rejected(user_service):
    user_service.create_user(CreateUserRequest(fullName="Dated", email="dated@sandvik.com", startDate="2026-05-01"))
    result = user_service.import_users(parse_csv(b"Name,Email,End Date\nDated,dated@sandvik.com,2026-04-01\n"))
    assert (result.created, result.updated) == (0, 0)
    assert len(result.errors) == 1


def test_import_rejects_wrong_domain_rows(user_service):
    result = user_service.import_users(parse_csv(b"Name,Email\nA,a@othercorp.com\n"))
    assert result.created == 0 and len(result.errors) == 1


def test_sync_coe_admins_promotes_and_demotes(user_service, repo):
    result = user_service.sync_coe_admins(["Employee1@Sandvik.com", "ghost@sandvik.com"])
    assert result.promoted == ["employee1@sandvik.com"]
    assert result.demoted == []
    assert result.unknown == ["ghost@sandvik.com"]
    assert user_service.get_me("employee1@sandvik.com").isAdmin is True

    # Resending the same set changes nothing; dropping the email demotes them again.
    assert user_service.sync_coe_admins(["employee1@sandvik.com"]).promoted == []
    result = user_service.sync_coe_admins([])
    assert result.demoted == ["employee1@sandvik.com"]
    assert user_service.get_me("employee1@sandvik.com").isAdmin is False


def test_sync_coe_admins_never_demotes_config_admin(user_service):
    user_service.sync_coe_admins([])
    assert user_service.get_me("admin1@sandvik.com").isAdmin is True


def test_coe_admin_flag_survives_profile_edit(user_service):
    user_service.sync_coe_admins(["employee1@sandvik.com"])
    user_service.update_user("employee1@sandvik.com", UpdateUserRequest(fullName="Renamed"))
    assert user_service.get_me("employee1@sandvik.com").isAdmin is True
