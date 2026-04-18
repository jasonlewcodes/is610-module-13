from uuid import uuid4

import pytest
import requests


def _base(fastapi_server: str) -> str:
    return fastapi_server.rstrip("/")


def _register_via_api(base_url: str, username: str, password: str) -> None:
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": f"{username}@example.com",
        "username": username,
        "password": password,
        "confirm_password": password,
    }
    response = requests.post(f"{base_url}/auth/register", json=payload)
    assert response.status_code == 201, f"Pre-registration failed: {response.text}"


# ---------------------------------------------------------------------------
# Positive: Register with valid data
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_register_valid_data(page, fastapi_server):
    """Fill the register form with valid data; intercept the API response to
    confirm 201, then verify the success alert appears."""
    base = _base(fastapi_server)
    uid = uuid4().hex[:8]

    page.goto(f"{base}/register")
    page.wait_for_load_state("domcontentloaded")

    page.fill("#username", f"user_{uid}")
    page.fill("#email", f"user_{uid}@example.com")
    page.fill("#first_name", "Alice")
    page.fill("#last_name", "Smith")
    page.fill("#password", "ValidPass1!")
    page.fill("#confirm_password", "ValidPass1!")

    with page.expect_response("**/auth/register") as resp_info:
        page.click('button[type="submit"]')

    resp = resp_info.value
    assert resp.status == 201, (
        f"Expected 201 from /auth/register, got {resp.status}: {resp.text()}"
    )

    page.wait_for_selector("#successAlert:not(.hidden)", timeout=5000)
    text = page.inner_text("#successMessage")
    assert "Registration successful" in text, f"Unexpected success text: {text!r}"


# ---------------------------------------------------------------------------
# Positive: Login with correct credentials
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_login_valid_credentials(page, fastapi_server):
    """Login through the UI with correct credentials; confirm 200 from the
    server, success alert visible, and token stored in localStorage."""
    base = _base(fastapi_server)
    uid = uuid4().hex[:8]
    username = f"loginuser_{uid}"
    password = "ValidPass1!"

    _register_via_api(base, username, password)

    page.goto(f"{base}/login")
    page.wait_for_load_state("domcontentloaded")

    page.fill("#username", username)
    page.fill("#password", password)

    with page.expect_response("**/auth/login") as resp_info:
        page.click('button[type="submit"]')

    resp = resp_info.value
    assert resp.status == 200, (
        f"Expected 200 from /auth/login, got {resp.status}: {resp.text()}"
    )

    page.wait_for_selector("#successAlert:not(.hidden)", timeout=5000)
    text = page.inner_text("#successMessage")
    assert "Login successful" in text, f"Unexpected success text: {text!r}"

    token = page.evaluate("localStorage.getItem('access_token')")
    assert token and len(token) > 0, "Expected access_token in localStorage after login"


# ---------------------------------------------------------------------------
# Negative: Register with a short / weak password → front-end error only
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_register_short_password_shows_error(page, fastapi_server):
    """Submit the register form with a weak password; the client-side guard
    must show an error without making any server call."""
    base = _base(fastapi_server)
    uid = uuid4().hex[:8]

    page.goto(f"{base}/register")
    page.wait_for_load_state("domcontentloaded")

    page.fill("#username", f"user_{uid}")
    page.fill("#email", f"user_{uid}@example.com")
    page.fill("#first_name", "Bob")
    page.fill("#last_name", "Jones")
    page.fill("#password", "short")        # fails length + uppercase + digit checks
    page.fill("#confirm_password", "short")
    page.click('button[type="submit"]')

    # Client-side validation fires synchronously — no network round-trip needed
    page.wait_for_selector("#errorAlert:not(.hidden)", timeout=3000)
    error_text = page.inner_text("#errorMessage")
    assert "password" in error_text.lower(), (
        f"Expected a password-related error, got: {error_text!r}"
    )
    assert page.query_selector("#successAlert.hidden") is not None, (
        "Success alert should not be visible when registration fails"
    )


# ---------------------------------------------------------------------------
# Negative: Login with wrong password → server 401, UI shows error
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_login_wrong_password_shows_error(page, fastapi_server):
    """Submit the login form with an incorrect password; confirm the server
    returns 401 and the UI displays an invalid-credentials error."""
    base = _base(fastapi_server)
    uid = uuid4().hex[:8]
    username = f"wrongpw_{uid}"
    correct = "ValidPass1!"
    wrong = "WrongPass9!"

    _register_via_api(base, username, correct)

    page.goto(f"{base}/login")
    page.wait_for_load_state("domcontentloaded")

    page.fill("#username", username)
    page.fill("#password", wrong)

    with page.expect_response("**/auth/login") as resp_info:
        page.click('button[type="submit"]')

    resp = resp_info.value
    assert resp.status == 401, (
        f"Expected 401 from /auth/login, got {resp.status}: {resp.text()}"
    )

    page.wait_for_selector("#errorAlert:not(.hidden)", timeout=5000)
    error_text = page.inner_text("#errorMessage")
    assert "invalid" in error_text.lower() or "password" in error_text.lower(), (
        f"Expected invalid-credentials message, got: {error_text!r}"
    )
    assert page.query_selector("#successAlert.hidden") is not None, (
        "Success alert should not be visible after a failed login"
    )
