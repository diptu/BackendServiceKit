from uuid import uuid4

import pytest
from fastapi import HTTPException, status

# ==============================================================================
# FIXTURES & UTILITIES
# ==============================================================================


@pytest.fixture
def unique_email() -> str:
    """Provides a fresh, unique email for isolated test cases."""
    return f"dev-{uuid4().hex[:8]}@example.com"


# ==============================================================================
# REGISTER ENDPOINT TESTS
# ==============================================================================


class TestRegister:
    @pytest.mark.anyio
    async def test_register_success(self, client, mocker, unique_email):
        """Should return 201 and user metadata when payload is valid."""
        # Arrange
        mock_hash = mocker.patch(
            "app.services.auth.hash_password", return_value="hashed_pass"
        )

        payload = {
            "email": unique_email,
            "password": "SecurePassword123!",
            "username": "ai_engineer",
        }

        # Act
        response = await client.post("/api/v1/auth/register", json=payload)
        response_data = response.json()

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response_data
        assert response_data["email"] == payload["email"]
        mock_hash.assert_called_once_with("SecurePassword123!")

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ("missing_field", "payload"),
        [
            ("email", {"password": "SecurePassword123!"}),
            ("password", {"email": "u1@example.com"}),
        ],
    )
    async def test_register_missing_fields_returns_422(
        self, client, missing_field, payload
    ):
        """Validates schema validation failure constraints when core components are absent."""
        # Act
        response = await client.post("/api/v1/auth/register", json=payload)
        response_data = response.json()

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "detail" in response_data

        # Verify that the specific missing field is identified in the error location path
        error_locs = [err["loc"] for err in response_data["detail"]]
        assert any("body" in loc and missing_field in loc for loc in error_locs)

    @pytest.mark.anyio
    async def test_register_duplicate_email_returns_409(
        self, client, mocker, unique_email
    ):
        """Ensures system handles duplicate email exceptions by returning 409 Conflict."""
        # Arrange
        mocker.patch(
            "app.services.auth.AuthService.register",
            side_effect=HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            ),
        )

        payload = {
            "email": unique_email,
            "password": "Password123!",
            "username": "existing",
        }

        # Act
        response = await client.post("/api/v1/auth/register", json=payload)

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "Email already registered."