# MiniProj Image Classification Server

This project implements the API described in `interface.md` and provides a small browser UI for registration, login, and image upload.

## Code Structure

- `web/app.py`  
  Flask server, API endpoints, UI page routes, and status tracking.

- `web/auth.py`  
  In-memory user and token management.

- `web/model.py`  
  Image classification logic using a pretrained ResNet18 model.

- `web/templates/`  
  Server-rendered HTML pages:
  - `auth.html` for login/register
  - `upload.html` for image upload

- `web/static/`  
  Frontend assets:
  - `styles.css`
  - `auth.js`
  - `upload.js`

- `tests/`  
  API and UI smoke tests based on the requirements in `interface.md`.

- `docker-compose.yml`  
  Runs the web app.

- `docker-compose.tests.yml`  
  Runs the web app and the test suite.

## Run With Docker

From the project root:

```powershell
docker compose up --build
```

Then open this page in the browser:

```text
http://localhost:5000/
```

UI flow:

- `/` shows the login/register page
- after successful login, the page redirects to `/upload`

To stop the containers:

```powershell
docker compose down
```

## Run Tests

To run the full automated test suite:

```powershell
docker compose -f docker-compose.tests.yml up --build --abort-on-container-exit --exit-code-from tests
```
