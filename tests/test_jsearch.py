"""JSearch connector: apply-link choice, board discovery and normalization."""

from packages.jobs_sources.detector import board_token_from_url
from packages.jobs_sources.jsearch import JSearchConnector, extract_items, pick_apply_link

ITEM = {
    "job_id": "abc123==",
    "employer_name": "Razorpay",
    "job_title": "Senior Data Analyst",
    "job_apply_link": "https://in.linkedin.com/jobs/view/123?utm_source=google",
    "apply_options": [
        {"publisher": "LinkedIn", "apply_link": "https://in.linkedin.com/jobs/view/123", "is_direct": False},
        {"publisher": "Razorpay Careers", "apply_link": "https://jobs.lever.co/razorpay/9f1c-22?lever-source=x", "is_direct": True},
    ],
    "job_description": "We need 3-5 years of experience with SQL, Python and Tableau. &amp;nbsp;Hybrid in Bengaluru.",
    "job_is_remote": False,
    "job_posted_at_datetime_utc": "2026-10-20T08:00:00.000Z",
    "job_city": "Bengaluru",
    "job_state": "Karnataka",
    "job_country": "IN",
    "job_employment_type": "FULLTIME",
    "job_min_salary": 1800000,
    "job_max_salary": 2400000,
    "job_salary_period": "YEAR",
}


def test_board_token_from_url() -> None:
    assert board_token_from_url("https://jobs.lever.co/razorpay/abc") == ("lever", "razorpay")
    assert board_token_from_url("https://boards.greenhouse.io/postman/jobs/1") == ("greenhouse", "postman")
    assert board_token_from_url("https://job-boards.greenhouse.io/groww/jobs/7") == ("greenhouse", "groww")
    assert board_token_from_url("https://boards.greenhouse.io/embed/job_app?for=cred&token=1") == ("greenhouse", "cred")
    assert board_token_from_url("https://jobs.ashbyhq.com/zepto/uuid") == ("ashby", "zepto")
    assert board_token_from_url("https://acme.myworkdayjobs.com/x") == ("workday", None)
    assert board_token_from_url("https://in.linkedin.com/jobs/view/1") == ("unknown", None)


def test_prefers_auto_appliable_board() -> None:
    url, ats, token = pick_apply_link(ITEM)
    assert (ats, token) == ("lever", "razorpay")
    assert url.startswith("https://jobs.lever.co/razorpay/")


def test_falls_back_to_direct_then_default() -> None:
    item = {
        "job_apply_link": "https://in.linkedin.com/jobs/view/1",
        "apply_options": [{"apply_link": "https://careers.acme.in/1", "is_direct": True}],
    }
    assert pick_apply_link(item) == ("https://careers.acme.in/1", "unknown", None)
    assert pick_apply_link({"job_apply_link": "https://naukri.com/x"})[0] == "https://naukri.com/x"


def test_normalize() -> None:
    conn = JSearchConnector(query="Data Analyst jobs in Bengaluru")
    job = conn.normalize(conn.to_raw(ITEM))
    assert job.source == "jsearch"
    assert job.company_name == "Razorpay"
    assert job.ats_type == "lever" and job.ats_board_token == "razorpay"
    assert "Bengaluru" in job.locations
    assert job.country == "India"
    assert job.employment_type == "full-time"
    assert (job.salary_min_lpa, job.salary_max_lpa) == (18.0, 24.0)
    assert (job.experience_min, job.experience_max) == (3, 5)
    assert "&nbsp;" not in job.description_text and "&amp;" not in job.description_text
    assert job.posted_at is not None and job.posted_at.year == 2026
    assert "lever-source" in job.application_url or job.application_url.startswith("https://jobs.lever.co/")


def test_monthly_and_foreign_salary() -> None:
    conn = JSearchConnector(query="x")
    monthly = conn.normalize(conn.to_raw({**ITEM, "job_min_salary": 100000, "job_max_salary": 150000, "job_salary_period": "MONTH", "job_description": "SQL"}))
    assert (monthly.salary_min_lpa, monthly.salary_max_lpa) == (12.0, 18.0)
    foreign = conn.normalize(conn.to_raw({**ITEM, "job_country": "US", "job_description": "SQL"}))
    assert foreign.salary_min_lpa is None
    assert foreign.country == "US"


def test_extract_items_v1_and_v2() -> None:
    assert extract_items({"data": [ITEM]}) == [ITEM]
    assert extract_items({"data": {"jobs": [ITEM]}}) == [ITEM]
    assert extract_items({"status": "ERROR"}) == []
