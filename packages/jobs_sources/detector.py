"""ATS type detector based on URL patterns."""

from urllib.parse import urlparse


def detect_ats(url: str) -> str:
    """Identify ATS type from an application or job listing URL.

    Recognized platforms:
    - greenhouse: boards.greenhouse.io, job-boards.greenhouse.io
    - lever: jobs.lever.co
    - ashby: jobs.ashbyhq.com
    - workday: *.myworkdayjobs.com
    - smartrecruiters: jobs.smartrecruiters.com
    - workable: apply.workable.com
    - recruitee: *.recruitee.com
    - keka: *.keka.com
    - darwinbox: *.darwinbox.in / *.darwinbox.com
    - zohorecruit: *.zohorecruit.com
    """
    if not url:
        return "unknown"

    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()

        if "greenhouse.io" in hostname:
            return "greenhouse"
        if "lever.co" in hostname:
            return "lever"
        if "ashbyhq.com" in hostname:
            return "ashby"
        if "myworkdayjobs.com" in hostname:
            return "workday"
        if "smartrecruiters.com" in hostname:
            return "smartrecruiters"
        if "workable.com" in hostname:
            return "workable"
        if "recruitee.com" in hostname:
            return "recruitee"
        if "keka.com" in hostname:
            return "keka"
        if "darwinbox.in" in hostname or "darwinbox.com" in hostname:
            return "darwinbox"
        if "zohorecruit.com" in hostname or "zohorecruit" in path:
            return "zohorecruit"

    except Exception:
        pass

    return "unknown"
