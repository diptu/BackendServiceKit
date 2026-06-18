import pytest
from fastapi import status

# ==============================================================================
# LOGIN ENDPOINT TESTS
# ==============================================================================


@pytest.mark.anyio
class TestLogin:
    @pytest.fixture
    def seeded_user(self, mocker):
        """Utility fixture to mock the AuthService return value matching TokenMatrixResponse."""
        from datetime import UTC, datetime
        from uuid import UUID

        from app.schemas.user import TokenMatrixResponse, UserOut, UserProfileOut

        user_out = UserOut(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            email="auth_user@example.com",
            is_active=True,
            is_verified=True,
            is_superuser=False,
            last_login_at=datetime(2026, 6, 14, 23, 21, tzinfo=UTC),
            created_at=datetime(2026, 6, 14, 23, 21, tzinfo=UTC),
            updated_at=datetime(2026, 6, 14, 23, 21, tzinfo=UTC),
            roles=[],
            profile=UserProfileOut(full_name="Authenticated User"),
        )
        mock_response = TokenMatrixResponse(
            access_token="mocked_access_jwt_token_string",
            refresh_token="mocked_refresh_jwt_token_string",
            token_type="Bearer",
            user=user_out,
        )

        mocker.patch(
            "app.services.auth.AuthService.login", return_value=mock_response
        )
        # Return a plain dict so existing assertions keep working unchanged
        return mock_response.model_dump(mode="json")

    async def test_login_success(self, client, seeded_user, mocker):
        """Should return 200 and a valid JWT token upon correct credentials."""
        # Arrange
        mocker.patch("app.core.security.verify_password", return_value=True)
        payload = {
            "username": seeded_user["user"]["email"],
            "password": "CorrectPassword123",
        }

        # Act
        response = await client.post("/api/v1/auth/login", data=payload)

        # Assert
        assert response.status_code == status.HTTP_200_OK

        resp_data = response.json()
        assert resp_data["access_token"] == seeded_user["access_token"]
        assert resp_data["token_type"] == seeded_user["token_type"]
        assert resp_data["user"]["email"] == seeded_user["user"]["email"]

    @pytest.mark.parametrize(
        ("username", "password", "expected_status"),
        [
            ("auth_user@example.com", "WrongPassword!", status.HTTP_401_UNAUTHORIZED),
            ("nonexistent@example.com", "SomePassword!", status.HTTP_401_UNAUTHORIZED),
            ("", "", status.HTTP_422_UNPROCESSABLE_ENTITY),
        ],
    )
    async def test_login_invalid_credentials(
        self, client, mocker, username, password, expected_status
    ):
        """Verifies authentication failures catch standard vectors without leaking system states."""
        mocker.patch("app.core.security.verify_password", return_value=False)
        payload = {"username": username, "password": password}

        # Act
        response = await client.post("/api/v1/auth/login", data=payload)

        # Assert
        assert response.status_code == expected_status

        if expected_status == status.HTTP_401_UNAUTHORIZED:
            resp_data = response.json()
            assert "Invalid credentials." in resp_data["detail"]

    async def test_login_route_not_found(self, client):
        """Verifies hitting an invalid or missing route target gracefully falls back to a 404 Status."""
        payload = {
            "username": "auth_user@example.com",
            "password": "CorrectPassword123",
        }

        # Act
        response = await client.post("/api/v1/auth/invalid-endpoint-slug", data=payload)

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

        resp_data = response.json()
        assert "detail" in resp_data
        assert resp_data["detail"] == "Not Found"
