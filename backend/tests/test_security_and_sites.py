"""
Unit tests for the auto-apply security layer and site detection.

Run from backend/:
    python -m pytest tests/test_security_and_sites.py -v

No DB, no network — pure logic. Env vars are manipulated with monkeypatch
so nothing leaks between tests.
"""
import pytest

from security.crypto import (
    CredentialCryptoError,
    encrypt_secret,
    decrypt_secret,
    encryption_configured,
    mask_username,
)
from browser.sites import detect_site, UnsupportedSiteError
from application.context import split_name, _highest_education, build_form_profile


FERNET_KEY = "Td1Pj0CKrJctD8feG__8oNoro5w-1OFWz1oXSYKdDtM="  # random test key
PASSPHRASE = "correct horse battery staple"


# ---------------------------------------------------------------------------
# crypto
# ---------------------------------------------------------------------------

class TestCrypto:
    def test_roundtrip_real_fernet_key(self, monkeypatch):
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", FERNET_KEY)
        ct = encrypt_secret("hunter2")
        assert ct != "hunter2"
        assert "hunter2" not in ct
        assert decrypt_secret(ct) == "hunter2"

    def test_roundtrip_passphrase_key(self, monkeypatch):
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", PASSPHRASE)
        ct = encrypt_secret("s3cret!")
        assert decrypt_secret(ct) == "s3cret!"

    def test_ciphertext_is_non_deterministic(self, monkeypatch):
        # Fernet includes a timestamp+IV: same plaintext → different ciphertext.
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", FERNET_KEY)
        assert encrypt_secret("x") != encrypt_secret("x")

    def test_tampered_ciphertext_rejected(self, monkeypatch):
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", FERNET_KEY)
        ct = encrypt_secret("topsecret")
        tampered = ct[:-4] + ("AAAA" if ct[-4:] != "AAAA" else "BBBB")
        with pytest.raises(CredentialCryptoError, match="changed"):
            decrypt_secret(tampered)

    def test_wrong_key_rejected(self, monkeypatch):
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", FERNET_KEY)
        ct = encrypt_secret("topsecret")
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", PASSPHRASE)
        with pytest.raises(CredentialCryptoError):
            decrypt_secret(ct)

    def test_missing_key_refuses_to_encrypt(self, monkeypatch):
        monkeypatch.delenv("CREDENTIAL_ENCRYPTION_KEY", raising=False)
        assert encryption_configured() is False
        with pytest.raises(CredentialCryptoError, match="not set"):
            encrypt_secret("pw")

    def test_missing_key_refuses_to_decrypt(self, monkeypatch):
        monkeypatch.delenv("CREDENTIAL_ENCRYPTION_KEY", raising=False)
        with pytest.raises(CredentialCryptoError):
            decrypt_secret("gAAAAABm")

    def test_blank_key_counts_as_unconfigured(self, monkeypatch):
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "   ")
        assert encryption_configured() is False


class TestMaskUsername:
    def test_email_masked(self):
        masked = mask_username("vaishvik@gmail.com")
        # Local part reduced to a short head + stars; domain untouched.
        assert masked.endswith("@gmail.com")
        head, _, domain = masked.partition("@")
        assert head.startswith("va")
        assert set(head) <= {"v", "a", "*"}
        assert domain == "gmail.com"

    def test_short_local_part(self):
        masked = mask_username("a@b.co")
        assert "@" in masked
        assert "a@" not in masked  # local part never fully shown... except len<=2 head overlap is fine
        assert "*" in masked.split("@")[0]

    def test_no_at_sign(self):
        assert mask_username("joedoe") == "j****e"
        assert mask_username("x") == "*"
        assert mask_username("") is None
        assert mask_username(None) is None


# ---------------------------------------------------------------------------
# site detection / whitelist policy
# ---------------------------------------------------------------------------

class TestDetectSite:
    def test_jobbank(self):
        flow = detect_site("https://jobbank.gc.ca/jobreport/jobposting/12345")
        assert flow.key == "jobbank"
        assert flow.requires_login is True

    def test_greenhouse_subdomain(self):
        flow = detect_site("https://boards.greenhouse.io/acme/jobs/999")
        assert flow.key == "greenhouse"
        assert flow.requires_login is False

    def test_lever(self):
        flow = detect_site("https://jobs.lever.co/acme/abc123")
        assert flow.key == "lever"

    def test_localhost_uses_mock_flow(self):
        for host in ("http://localhost:8000/mock-apply/job", "http://127.0.0.1:9000/x"):
            flow = detect_site(host)
            assert flow.requires_login is True  # mock login form is part of the E2E

    def test_unknown_host_generic_no_login(self):
        flow = detect_site("https://careers.some-random-company.com/apply/42")
        assert flow.key == "generic"
        assert flow.requires_login is False

    @pytest.mark.parametrize("url", [
        "https://www.linkedin.com/jobs/view/12345",
        "https://linkedin.com/jobs/view/12345",
        "https://ca.indeed.com/viewjob?jk=abc",
        "https://indeed.com/viewjob?jk=abc",
    ])
    def test_blocked_hosts_raise(self, url):
        with pytest.raises(UnsupportedSiteError):
            detect_site(url)

    def test_empty_url_raises(self):
        with pytest.raises(UnsupportedSiteError):
            detect_site("")
        with pytest.raises(UnsupportedSiteError):
            detect_site(None)


# ---------------------------------------------------------------------------
# form profile derivation
# ---------------------------------------------------------------------------

class _FakeProfile:
    """Just enough attribute surface for build_form_profile."""

    def __init__(self, **kw):
        defaults = dict(
            name="", email="", phone="", address="", city="", province="",
            postal_code="", country="", work_authorization="",
            linkedin_url="", portfolio_url="", github_url="",
            education=[], employment_history=[], skills=[],
            certifications=[], salary_expectation_min=None,
            salary_expectation_max=None, notice_period_weeks=2,
        )
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(self, k, v)


class TestNameSplit:
    def test_two_parts(self):
        assert split_name("Vaishvik Patel") == ("Vaishvik", "Patel")

    def test_three_parts_middle_goes_first(self):
        assert split_name("Jean Luc Picard") == ("Jean Luc", "Picard")

    def test_single_part(self):
        assert split_name("Cher") == ("Cher", "")

    def test_empty(self):
        assert split_name("") == ("", "")
        assert split_name(None) == ("", "")


class TestHighestEducation:
    def test_picks_phd_over_bachelor(self):
        edu = [{"degree": "Bachelor of Technology"}, {"degree": "PhD in CS"}]
        assert _highest_education(edu) == "Phd"

    def test_master_beats_bachelor(self):
        assert _highest_education([{"degree": "Bachelor"}, {"degree": "Master of Science"}]) == "Master"

    def test_empty_returns_empty_string(self):
        assert _highest_education([]) == ""
        assert _highest_education([{"degree": "Quantum Underwater Basketweaving"}]) == ""


class TestBuildFormProfile:
    def test_full_profile_no_derived_gaps(self):
        profile = _FakeProfile(
            name="Vaishvik Patel",
            email="va@example.com",
            phone="+1 555 0100",
            work_authorization="Canadian citizen",
            education=[{"degree": "Bachelor of Engineering"}],
            employment_history=[{"start_date": "2022-05", "end_date": "2026-01"}],
        )
        fp, derived = build_form_profile(profile)
        assert fp["first_name"] == "Vaishvik"
        assert fp["last_name"] == "Patel"
        # Calendar-year arithmetic: 2022→2026 counts as 4 (partial years
        # round up) — an approximation, which is why it's review-flagged.
        assert fp["years_of_experience"] == "4"
        assert derived == []

    def test_missing_fields_flagged_for_review(self):
        profile = _FakeProfile(name="Cher", email="c@x.io")  # no phone/work_auth/education
        fp, derived = build_form_profile(profile)
        assert set(derived) >= {"last_name", "phone", "work_authorization", "education_level"}
        assert fp["years_of_experience"] == ""

    def test_country_defaults_canada(self):
        fp, _ = build_form_profile(_FakeProfile())
        assert fp["country"] == "Canada"
