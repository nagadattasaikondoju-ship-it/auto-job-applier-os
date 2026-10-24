# Canonical mapping dictionary of field label synonyms found across Greenhouse, Lever, Ashby, Workday, and Indian HRMS application forms.
FIELD_SYNONYMS: dict[str, str] = {
    # Full Name / Name parts
    "full name": "full_name",
    "name": "full_name",
    "candidate name": "full_name",
    "applicant name": "full_name",
    "first name": "first_name",
    "given name": "first_name",
    "last name": "last_name",
    "surname": "last_name",
    "family name": "last_name",
    # Contact Details
    "email": "email",
    "email address": "email",
    "primary email": "email",
    "phone": "phone",
    "phone number": "phone",
    "mobile": "phone",
    "mobile number": "phone",
    "contact number": "phone",
    "cell phone": "phone",
    "whatsapp number": "phone",
    # Location & Address
    "city": "city",
    "current city": "city",
    "current location": "city",
    "location": "city",
    "state": "state",
    "province": "state",
    "country": "country",
    "pincode": "pincode",
    "postal code": "pincode",
    "zip code": "pincode",
    "address": "address",
    "current address": "address",
    # Compensation (CTC)
    "current ctc": "current_ctc_lpa",
    "current ctc (in lpa)": "current_ctc_lpa",
    "current fixed ctc": "current_ctc_lpa",
    "current annual salary": "current_ctc_lpa",
    "current compensation": "current_ctc_lpa",
    "present ctc": "current_ctc_lpa",
    "present salary": "current_ctc_lpa",
    "expected ctc": "expected_ctc_lpa",
    "expected ctc (in lpa)": "expected_ctc_lpa",
    "expected annual salary": "expected_ctc_lpa",
    "expected compensation": "expected_ctc_lpa",
    "desired salary": "expected_ctc_lpa",
    "salary expectations": "expected_ctc_lpa",
    # Notice Period & Availability
    "notice period": "notice_period_days",
    "notice period (in days)": "notice_period_days",
    "official notice period": "notice_period_days",
    "how soon can you join": "notice_period_days",
    "days to join": "notice_period_days",
    "availability": "notice_period_days",
    "are you currently serving notice": "currently_serving_notice",
    "serving notice period": "currently_serving_notice",
    "serving notice": "currently_serving_notice",
    "last working day": "last_working_day",
    "lwd": "last_working_day",
    # Experience & Seniority
    "total experience": "total_experience_years",
    "total years of experience": "total_experience_years",
    "relevant experience": "relevant_experience_years",
    "years of experience": "total_experience_years",
    "current company": "current_company",
    "current employer": "current_company",
    "present company": "current_company",
    "current title": "current_title",
    "current designation": "current_title",
    "current role": "current_title",
    # Links & Profiles
    "linkedin": "linkedin_url",
    "linkedin url": "linkedin_url",
    "linkedin profile": "linkedin_url",
    "linkedin profile url": "linkedin_url",
    "github": "github_url",
    "github url": "github_url",
    "github profile": "github_url",
    "github profile url": "github_url",
    "portfolio": "portfolio_url",
    "portfolio url": "portfolio_url",
    "website": "portfolio_url",
    "personal website": "portfolio_url",
    "leetcode": "leetcode_url",
    "leetcode profile": "leetcode_url",
    # Documents & Files
    "resume": "resume_file",
    "cv": "resume_file",
    "upload resume": "resume_file",
    "attach resume": "resume_file",
    "cover letter": "cover_letter_file",
    "upload cover letter": "cover_letter_file",
    "attach cover letter": "cover_letter_file",
    # Legal & Work Authorization
    "work authorization": "work_authorization",
    "authorized to work in india": "work_authorization_india",
    "are you legally authorized to work in india": "work_authorization_india",
    "visa sponsorship": "visa_sponsorship_needed",
    "will you now or in the future require visa sponsorship": "visa_sponsorship_needed",
    "require sponsorship": "visa_sponsorship_needed",
    "willing to relocate": "willing_to_relocate",
    "are you open to relocation": "willing_to_relocate",
    # Education & Academics (India-specific forms)
    "highest qualification": "degree",
    "degree": "degree",
    "graduation college": "college",
    "college / university": "college",
    "institution": "college",
    "graduation year": "graduation_year",
    "year of passing": "graduation_year",
    "cgpa": "grade",
    "percentage": "grade",
    "10th marks": "board_10th_grade",
    "12th marks": "board_12th_grade",
    # Behavioral / Story Questions
    "why do you want to work here": "why_this_company",
    "why this company": "why_this_company",
    "why applyon": "why_this_company",
    "tell us about yourself": "tell_us_about_yourself",
    "tell me about yourself": "tell_us_about_yourself",
    "brief introduction": "tell_us_about_yourself",
    "what is your greatest achievement": "biggest_achievement",
    "describe a challenging project": "challenging_project",
    "reason for leaving": "reason_for_leaving_current_job",
    "why are you looking for a change": "reason_for_leaving_current_job",
    "how did you hear about us": "how_did_you_hear",
    "how did you find this job": "how_did_you_hear",
    "source": "how_did_you_hear",
}


def normalize_field_label(label: str) -> str:
    """Strip punctuation and whitespace from an extracted label to look up canonical key."""
    clean = label.strip().lower()
    for char in [":", "*", "(required)", "(optional)", "?", "-"]:
        clean = clean.replace(char, "")
    clean = " ".join(clean.split())
    return clean


def lookup_canonical_field(label: str) -> str | None:
    """Return canonical key if a direct synonym match exists."""
    clean = normalize_field_label(label)
    return FIELD_SYNONYMS.get(clean)
