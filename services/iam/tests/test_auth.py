def test_jwt_payload_validation():
    # A simple placeholder test for your Auth logic
    mock_payload = {"sub": "user_123", "role": "admin"}

    assert "sub" in mock_payload
    assert mock_payload["role"] == "admin"
