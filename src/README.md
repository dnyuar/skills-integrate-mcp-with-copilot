# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher-only student registration and unregistration
- Teacher sign-in with credentials stored as password hashes in `teachers.json`

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   uvicorn src.app:app --reload
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc
   - Activities page: http://localhost:8000/

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/session`                                                   | Check whether the current browser session is signed in as a teacher |
| POST   | `/auth/login`                                                     | Sign in with a teacher username and password                        |
| POST   | `/auth/logout`                                                    | Sign out and invalidate the current teacher session                 |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only student registration                                  |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only student unregistration                             |

## Configure teacher accounts

Teacher usernames and salted PBKDF2-HMAC-SHA256 password hashes are stored in
`src/teachers.json`. The file is checked by the backend when a teacher signs
in. To create a hash, run this snippet locally and enter the generated record
in the `teachers` array. The password is prompted for and is not written to
the file:

```python
import getpass
import hashlib
import json
import secrets

username = input("Teacher username: ")
password = getpass.getpass("Teacher password: ")
salt = secrets.token_bytes(16)
record = {
    "username": username,
    "password_salt": salt.hex(),
    "password_hash": hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 600_000
    ).hex(),
}
print(json.dumps(record, indent=2))
```

For example, add the printed object to the file in this format:

```json
{
  "teachers": [
    {
      "username": "teacher1",
      "password_salt": "<generated salt>",
      "password_hash": "<generated hash>"
    }
  ]
}
```

The browser session uses an HTTP-only, same-site cookie and expires after eight
hours. Activity viewing remains public; registration and unregistration are
also protected by the API, not only by the browser interface.

Run the access-control tests from the repository root with:

```
python -m unittest src.test_app
```

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
