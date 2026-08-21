"""
End-to-end test: auto-apply against the local mock target.

Run from backend/:
    python tests/e2e_mock_apply.py

Uses a scratch SQLite DB (never production Supabase) and the env-gated
/mock-apply/* routes. Verifies:
  1. AUTO blocked with 400 while AUTO_SUBMIT=false
  2. MANUAL apply -> parked NEEDS_HUMAN_INPUT + screenshot
  3. Confirm submit -> APPLIED with MOCK- confirmation number
  4. AUTO apply works once AUTO_SUBMIT=true
  5. Credentials API round-trip (save -> masked list -> delete), password
     never in any response or server log
"""
import asyncio
import os
import pathlib
import subprocess
import sys
import time

BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))  # allow importing backend modules (security, …)
SCRATCH_DB = BACKEND / "output" / "e2e_scratch.db"
RESUME_FILE = BACKEND / "output" / "e2e_resume.docx"
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
LOG_FILE = BACKEND / "output" / "e2e_server.log"

ENV = {
    **os.environ,
    "DATABASE_URL": f"sqlite+aiosqlite:///{SCRATCH_DB}",
    "ENABLE_MOCK_APPLY_TARGET": "1",
    "HEADLESS": "true",
    "CREDENTIAL_ENCRYPTION_KEY": "e2e-test-key-not-production",
    # AUTO_SUBMIT intentionally unset for phase A of the test.
}
# The seeding step imports backend modules in THIS process too — make sure
# it sees the same scratch configuration as the server subprocess.
os.environ.update({k: v for k, v in ENV.items() if k in (
    "DATABASE_URL", "ENABLE_MOCK_APPLY_TARGET", "HEADLESS", "CREDENTIAL_ENCRYPTION_KEY",
)})

PASSES = []
FAILURES = []


def check(name, cond, detail=""):
    if cond:
        PASSES.append(name)
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


async def seed():
    """Seed profile/job/resume/application + mock credential in scratch DB.

    Uses the ORM so Python-side column defaults apply.
    """
    from database.database import async_session_factory
    from database.models import (
        Application, ApplicationStatus, CandidateProfile, Job, Resume, SiteCredential,
    )
    from security.crypto import encrypt_secret

    SCRATCH_DB.parent.mkdir(exist_ok=True)
    RESUME_FILE.write_bytes(b"PK\x03\x04 e2e placeholder docx bytes")

    async with async_session_factory() as session:
        profile = CandidateProfile(
            name="E2E Candidate", email="e2e@example.com", phone="+1 555 0100",
            city="Toronto", province="ON", country="Canada",
            work_authorization="Canadian citizen",
            education=[{"degree": "Bachelor of Engineering"}],
            employment_history=[{"start_date": "2022-05", "end_date": "2026-01", "title": "Developer"}],
        )
        session.add(profile)

        job = Job(
            canonical_url=f"{BASE}/mock-apply/job", source_urls=[], source="mock",
            title="E2E Developer", company="MockCorp", location="Toronto, ON",
            description="Test posting", content_hash=f"e2e-{time.time()}",
            application_url=f"{BASE}/mock-apply/job",
        )
        session.add(job)
        await session.flush()

        resume = Resume(
            candidate_id=profile.id, job_id=job.id, version=1,
            file_path=str(RESUME_FILE), filename="e2e_resume.docx",
        )
        session.add(resume)
        await session.flush()  # assign resume.id before referencing it

        application = Application(
            candidate_id=profile.id, job_id=job.id, resume_id=resume.id,
            application_url=f"{BASE}/mock-apply/job", status=ApplicationStatus.READY,
        )
        session.add(application)

        session.add(SiteCredential(
            site="mock", username="tester@example.com",
            password_encrypted=encrypt_secret("correct-horse-battery"),
        ))
        await session.commit()
        return application.id


def api(method, path, expect=None, **kw):
    import httpx
    resp = httpx.request(method, BASE + path, timeout=30, **kw)
    if expect is not None:
        assert resp.status_code == expect, f"{method} {path} -> {resp.status_code}, wanted {expect}: {resp.text[:300]}"
    return resp


def poll_status(app_id, want, timeout_s=180):
    """Poll apply/status until `want` key becomes true."""
    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        last = api("GET", f"/applications/{app_id}/apply/status").json()["data"]
        if last.get(want):
            return last
        time.sleep(2)
    return last


def get_app(app_id):
    items = api("GET", "/applications?page=1&page_size=50").json()["data"]["items"]
    return next(a for a in items if int(a["id"]) == app_id)


def start_server(auto_submit=None):
    env = dict(ENV)
    if auto_submit is not None:
        env["AUTO_SUBMIT"] = auto_submit
    LOG_FILE.parent.mkdir(exist_ok=True)
    log = open(LOG_FILE, "ab")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1",
         "--port", str(PORT), "--log-level", "warning"],
        cwd=BACKEND, env=env, stdout=log, stderr=log,
    )
    import httpx
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            r = httpx.get(BASE + "/health", timeout=2)
            if r.status_code == 200:
                return proc
        except Exception:
            pass
        time.sleep(1)
    proc.kill()
    raise RuntimeError("server did not become healthy")


def reset_application(app_id):
    """Put the application back to READY_TO_APPLY for the next run."""
    api("PATCH", f"/applications/{app_id}", json={"status": "READY_TO_APPLY"}, expect=200)


def main():
    print("== E2E: mock apply target ==")
    SCRATCH_DB.unlink(missing_ok=True)
    LOG_FILE.unlink(missing_ok=True)

    server = start_server()

    try:
        app_id = asyncio.run(seed())
        print(f"Seeded application {app_id}")

        print("\n-- Phase A: auto blocked while AUTO_SUBMIT unset --")
        r = api("POST", f"/applications/{app_id}/apply", json={"mode": "auto"})
        check("auto rejected with 400", r.status_code == 400, f"got {r.status_code}: {r.text[:200]}")

        print("\n-- Phase B: manual fill -> park --")
        r = api("POST", f"/applications/{app_id}/apply", json={"mode": "manual"})
        check("manual accepted with 202", r.status_code == 202, f"got {r.status_code}: {r.text[:200]}")

        status = poll_status(app_id, "parked")
        check("run parked", status.get("parked") is True, f"final status: {status}")
        check(
            "status endpoint reports auto disabled",
            status.get("auto_submit_enabled") is False, str(status),
        )

        app = get_app(app_id)
        check("application status NEEDS_REVIEW", app.get("status") == "NEEDS_REVIEW", app.get("status"))
        check(
            "review reason mentions review",
            bool(app.get("needs_review_reason")) and "review" in app["needs_review_reason"].lower(),
            str(app.get("needs_review_reason")),
        )

        shot = api("GET", f"/applications/{app_id}/screenshot")
        check("screenshot served", shot.status_code == 200 and "image" in shot.headers.get("content-type", ""),
              f"{shot.status_code} {shot.headers.get('content-type')}")

        print("\n-- Phase C: confirm submit -> APPLIED --")
        conf = api("POST", f"/applications/{app_id}/apply/confirm").json()["data"]
        check("confirm reports submitted", conf.get("submitted") is True, str(conf))
        confirmation = (conf.get("confirmation_number") or "")
        check("confirmation number MOCK-", confirmation.startswith("MOCK-"), confirmation)

        app = get_app(app_id)
        # DB status APPLIED serializes to the product vocabulary "SUBMITTED";
        # the confirmation number rides out as external_application_id.
        check("application now SUBMITTED", app.get("status") == "SUBMITTED", app.get("status"))
        check("confirmation persisted", (app.get("external_application_id") or "").upper().startswith("MOCK-"),
              str(app.get("external_application_id")))

        print("\n-- Phase D: credentials round-trip --")
        secret_pw = "e2e-super-secret-pw"
        r = api("PUT", "/settings/credentials/jobbank",
                json={"username": "tester@example.com", "password": secret_pw})
        check("credential saved", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")
        body_text = ""
        for path in ("/settings/credentials", "/settings"):
            body_text += api("GET", path).text
        check("password never in responses", secret_pw not in body_text, "secret leaked in GET response")
        creds = api("GET", "/settings/credentials").json()["data"]
        site_names = [s["site"] for s in creds["sites"]]
        check("sites list carries names", all(site_names) and set(site_names) >= {"jobbank", "greenhouse", "lever"},
              str(site_names))
        jobbank = next((s for s in creds["sites"] if s["site"] == "jobbank"), {})
        check("jobbank configured", jobbank.get("configured") is True, str(jobbank))
        hint = jobbank.get("username_hint") or ""
        check("username masked", "tester@example.com" != hint and "*" in hint, hint)
        r = api("DELETE", "/settings/credentials/jobbank")
        check("credential deleted", r.status_code == 200, str(r.status_code))
        creds = api("GET", "/settings/credentials").json()["data"]
        jobbank = next((s for s in creds["sites"] if s["site"] == "jobbank"), None)
        # Either dropped from the list entirely or listed as unconfigured.
        check("jobbank cleared", jobbank is None or jobbank.get("configured") is False, str(jobbank))

    finally:
        server.terminate()
        server.wait(timeout=15)

    print("\n-- Phase E: AUTO_SUBMIT=true enables auto --")
    server = start_server(auto_submit="true")
    try:
        reset_application(app_id)
        r = api("POST", f"/applications/{app_id}/apply", json={"mode": "auto"})
        check("auto accepted with 202 when enabled", r.status_code == 202,
              f"{r.status_code}: {r.text[:200]}")
        status = poll_status(app_id, "running", timeout_s=240)
        # Wait for the run to finish entirely.
        deadline = time.time() + 120
        while time.time() < deadline and status.get("running"):
            time.sleep(3)
            status = api("GET", f"/applications/{app_id}/apply/status").json()["data"]
        app = get_app(app_id)
        check("auto run reached SUBMITTED", app.get("status") == "SUBMITTED",
              f"status={app.get('status')} reason={app.get('needs_review_reason') or app.get('failure_reason')}")
        check("auto confirmation stored", (app.get("external_application_id") or "").upper().startswith("MOCK-"),
              str(app.get("external_application_id")))
    finally:
        server.terminate()
        server.wait(timeout=15)

    print("\n-- Phase F: secrets never logged --")
    log_text = LOG_FILE.read_text(errors="ignore")
    check("mock password absent from logs", "correct-horse-battery" not in log_text)
    check("jobbank password absent from logs", "e2e-super-secret-pw" not in log_text)

    print(f"\n{'=' * 46}\n{len(PASSES)} passed, {len(FAILURES)} failed")
    for f in FAILURES:
        print(f"  FAIL {f}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
