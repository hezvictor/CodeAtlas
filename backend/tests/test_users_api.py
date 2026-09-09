def test_user_schemas_support_profile_and_password_changes():
    from app.schemas import PasswordUpdate, UserUpdate
    assert UserUpdate(nickname=" Alice ").nickname == " Alice "
    assert PasswordUpdate(current_password="old", new_password="new-password").new_password == "new-password"

def test_user_nickname_rejects_whitespace_only_values():
    from pydantic import ValidationError
    from app.schemas import RegisterRequest, UserUpdate
    for factory in (lambda: UserUpdate(nickname="   "), lambda: RegisterRequest(email="a@b.com", password="password123", nickname="  ")):
        try:
            factory()
        except ValidationError:
            continue
        raise AssertionError("whitespace-only nickname must be rejected")
