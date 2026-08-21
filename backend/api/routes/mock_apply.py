"""
Local mock apply target for E2E testing the auto-apply pipeline.

Enabled only with ENABLE_MOCK_APPLY_TARGET=1 (never set in production).
Serves a tiny ATS-like flow at /mock-apply/*:
  /login  -> login form (any stored credential works; wrong password fails)
  /job    -> application form (personal info + resume upload + screening q)
  /submit -> success page with a confirmation number

The apply pipeline treats localhost URLs via generic.mock_flow().
"""
import os
import secrets

from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

# username -> password accepted by the mock login
_MOCK_USERS = {"tester@example.com": "correct-horse-battery"}
_sessions: set = set()
_confirmations: dict = {}

ENABLED = os.getenv("ENABLE_MOCK_APPLY_TARGET", "").lower() in ("1", "true", "yes")

PAGE_STYLE = """
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
  label { display: block; margin-top: 14px; font-weight: 600; }
  input, textarea { width: 100%; padding: 8px; margin-top: 4px; box-sizing: border-box; }
  button { margin-top: 20px; padding: 10px 22px; }
  .ok { color: #0a7d33; font-size: 20px; }
</style>
"""


def _guard():
    if not ENABLED:
        return HTMLResponse("Mock apply target is disabled (set ENABLE_MOCK_APPLY_TARGET=1)", status_code=404)
    return None


@router.get("/mock-apply/login", response_class=HTMLResponse)
async def login_form():
    guard = _guard()
    if guard:
        return guard
    return HTMLResponse(f"""<html><head><title>Mock ATS — Login</title>{PAGE_STYLE}</head><body>
    <h1>Mock ATS — Sign in</h1>
    <form method="post" action="/mock-apply/do-login">
      <label>Username <input name="username" /></label>
      <label>Password <input name="password" type="password" /></label>
      <button id="login-submit" type="submit">Sign in</button>
    </form></body></html>""")


@router.post("/mock-apply/do-login")
async def do_login(username: str = Form(""), password: str = Form("")):
    guard = _guard()
    if guard:
        return guard
    if _MOCK_USERS.get(username) != password:
        return HTMLResponse(
            f"<html><body>{PAGE_STYLE}<h1>Login failed</h1><p>Wrong username or password.</p>"
            f"<a href='/mock-apply/login'>Try again</a></body></html>",
            status_code=200,
        )
    token = secrets.token_hex(16)
    _sessions.add(token)
    resp = RedirectResponse("/mock-apply/job", status_code=303)
    resp.set_cookie("mock_session", token)
    return resp


@router.get("/mock-apply/job", response_class=HTMLResponse)
async def job_form(mock_session: str = Cookie(default="")):
    guard = _guard()
    if guard:
        return guard
    logged_in = mock_session in _sessions
    login_state = f"<p>logged in as {_MOCK_USERS and 'tester@example.com'}</p>" if logged_in else "<p>Guest mode (not logged in)</p>"
    return HTMLResponse(f"""<html><head><title>Mock ATS — Apply</title>{PAGE_STYLE}</head><body>
    <h1>Mock ATS — Application</h1>{login_state}
    <form method="post" action="/mock-apply/submit" enctype="multipart/form-data">
      <label>First name <input name="first_name" /></label>
      <label>Last name <input name="last_name" /></label>
      <label>Email <input name="email" type="email" /></label>
      <label>Phone <input name="phone" type="tel" /></label>
      <label>Are you legally allowed to work in Canada?
        <select name="work_authorization">
          <option value="">Select...</option>
          <option value="yes">Yes</option>
          <option value="no">No</option>
        </select>
      </label>
      <label>Resume (docx) <input name="resume_file" type="file" /></label>
      <button type="submit">Submit Application</button>
    </form></body></html>""")


@router.post("/mock-apply/submit")
async def submit_application(
    request: Request,
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    work_authorization: str = Form(""),
):
    guard = _guard()
    if guard:
        return guard
    form = await request.form()
    resume_name = None
    upload = form.get("resume_file")
    if upload is not None and getattr(upload, "filename", ""):
        resume_name = upload.filename

    missing = [label for label, val in (
        ("first_name", first_name), ("last_name", last_name),
        ("email", email), ("work_authorization", work_authorization),
    ) if not str(val).strip()]
    if missing:
        return HTMLResponse(
            f"<html><body>{PAGE_STYLE}<h2>Error: missing required fields: {', '.join(missing)}</h2>"
            f"<a href='/mock-apply/job'>Back to form</a></body></html>", status_code=200)

    confirmation = f"MOCK-{secrets.token_hex(4).upper()}"
    _confirmations[email] = confirmation
    return HTMLResponse(f"""<html><head><title>Mock ATS</title>{PAGE_STYLE}</head><body>
    <h1 class="ok">Thank you for applying!</h1>
    <p>Your application has been submitted successfully.</p>
    <p>Confirmation: <strong>{confirmation}</strong></p>
    <p>Received resume: {resume_name or 'none'}</p>
    </body></html>""")


@router.get("/mock-apply/health")
async def mock_health():
    return {"enabled": ENABLED}
