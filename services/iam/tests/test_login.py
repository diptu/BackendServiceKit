# import pytest
# from app.main import app as app_instance

# # ==============================================================================
# # FIXTURES & CONFIGURATION
# # ==============================================================================

# @pytest.fixture(scope="session")
# def app():
#     """Provides the application instance."""
#     return app_instance


# @pytest.fixture
# def db_session(mocker):
#     """Provides a mocked or isolated DB session wrapper to avoid global state."""
#     # If using FastAPI dependency overrides, mock the engine/session dependency here
#     mock_session = mocker.MagicMock()
#     return mock_session


# ==============================================================================
# LOGIN ENDPOINT TESTS
# ==============================================================================

# class TestLogin:

#     @pytest.fixture
#     def seeded_user(self, app, mocker):
#         """Utility fixture to mock or inject a baseline user for auth scenarios."""
#         # Instead of risking a dirty global DB connection, we can mock the fetch layer
#         mock_user = mocker.MagicMock()
#         mock_user.email = "auth_user@example.com"
#         mock_user.password_hash = "hashed_val"
#         mock_user.username = "auth"

#         mocker.patch("app.services.UserService.get_user_by_email", return_value=mock_user)
#         return mock_user

#     def test_login_success(self, client, seeded_user, mocker):
#         """Should return 200 and a valid JWT token upon correct credentials."""
#         # Arrange
#         mocker.patch("app.utils.security.verify_password", return_value=True)
#         payload = {"email": "auth_user@example.com", "password": "CorrectPassword123"}

#         # Act
#         response = client.post("/api/v1/login", json=payload)

#         # Assert
#         assert response.status_code == 200
#         assert "access_token" in response.json
#         assert response.json["token_type"] == "Bearer"

#     @pytest.mark.parametrize(
#         "email, password, expected_status",
#         [
#             ("auth_user@example.com", "WrongPassword!", 401),  # Wrong pass
#             ("nonexistent@example.com", "SomePassword!", 401),  # Wrong user
#             ("", "", 400),                                      # Malformed payload
#         ],
#     )
#     def test_login_invalid_credentials(
#         self, client, mocker, email, password, expected_status
#     ):
#         """Verifies authentication failures catch standard vectors without leaking system states."""
#         mocker.patch("app.utils.security.verify_password", return_value=False)
#         payload = {"email": email, "password": password}

#         response = client.post("/api/v1/login", json=payload)

#         assert response.status_code == expected_status
#         if expected_status == 401:
#             assert "Invalid email or password" in response.json["error"]
