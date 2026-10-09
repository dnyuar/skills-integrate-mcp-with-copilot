import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src import app as app_module


class TeacherAccessTests(unittest.TestCase):
    username = "test-teacher"
    password = "test-password"

    def setUp(self):
        self.original_participants = {
            name: list(activity["participants"])
            for name, activity in app_module.activities.items()
        }
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.credentials_file = Path(self.temporary_directory.name) / "teachers.json"
        salt = b"test-salt-for-access-tests"
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            self.password.encode("utf-8"),
            salt,
            app_module.PASSWORD_HASH_ITERATIONS,
        ).hex()
        self.credentials_file.write_text(
            json.dumps(
                {
                    "teachers": [
                        {
                            "username": self.username,
                            "password_salt": salt.hex(),
                            "password_hash": password_hash,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.credentials_patch = patch.object(
            app_module, "TEACHERS_FILE", self.credentials_file
        )
        self.credentials_patch.start()
        app_module.teacher_sessions.clear()
        self.client = TestClient(app_module.app)

    def tearDown(self):
        self.client.close()
        app_module.teacher_sessions.clear()
        for name, participants in self.original_participants.items():
            app_module.activities[name]["participants"] = participants
        self.credentials_patch.stop()
        self.temporary_directory.cleanup()

    def test_activity_view_is_public(self):
        response = self.client.get("/activities")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Chess Club", response.json())

    def test_registration_changes_require_teacher_sign_in(self):
        signup_response = self.client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "unauthorized@mergington.edu"},
        )
        unregister_response = self.client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "michael@mergington.edu"},
        )

        self.assertEqual(signup_response.status_code, 401)
        self.assertEqual(unregister_response.status_code, 401)

    def test_teacher_can_register_unregister_and_sign_out(self):
        login_response = self.client.post(
            "/auth/login",
            json={"username": self.username, "password": self.password},
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(self.client.cookies.get("teacher_session"))
        self.assertEqual(
            self.client.get("/auth/session").json(),
            {"authenticated": True, "username": self.username},
        )

        signup_response = self.client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "new-student@mergington.edu"},
        )
        self.assertEqual(signup_response.status_code, 200)
        self.assertIn(
            "new-student@mergington.edu",
            self.client.get("/activities").json()["Chess Club"]["participants"],
        )

        unregister_response = self.client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "new-student@mergington.edu"},
        )
        self.assertEqual(unregister_response.status_code, 200)

        logout_response = self.client.post("/auth/logout")
        self.assertEqual(logout_response.status_code, 200)
        self.assertEqual(
            self.client.post(
                "/activities/Chess%20Club/signup",
                params={"email": "after-logout@mergington.edu"},
            ).status_code,
            401,
        )

    def test_invalid_credentials_are_rejected(self):
        response = self.client.post(
            "/auth/login",
            json={"username": self.username, "password": "incorrect"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("teacher_session", self.client.cookies)


if __name__ == "__main__":
    unittest.main()
