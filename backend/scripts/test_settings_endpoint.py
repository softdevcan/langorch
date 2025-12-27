import requests
import json

# Login
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "admin@test.com", "password": "admin123"}
)
login_data = login_response.json()
token = login_data["access_token"]

print(f"Login successful, token: {token[:50]}...")

# Test settings endpoint
headers = {"Authorization": f"Bearer {token}"}
settings_response = requests.get(
    "http://localhost:8000/api/v1/settings/embedding-provider",
    headers=headers
)

print(f"\nSettings endpoint response:")
print(f"Status: {settings_response.status_code}")
print(f"Body: {json.dumps(settings_response.json(), indent=2) if settings_response.status_code == 200 else settings_response.text}")
