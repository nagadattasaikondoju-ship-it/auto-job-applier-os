ApplyPilot — AI Job Application Copilot
ApplyPilot is an AI-powered job application platform that helps job seekers discover relevant roles, tailor their resume and cover letter for each job, autofill application forms, review submissions, and track their entire job search from one dashboard.

Tagline: Apply smarter. Interview sooner.

Problem
Job applications are repetitive and time-consuming:

Searching multiple job boards and career pages

Rewriting resumes and cover letters for every role

Filling the same personal and work-history details again and again

Losing track of where you applied and what resume version you used

Applying to irrelevant roles because of volume pressure

ApplyPilot removes the repetitive work while keeping the user in control of every final submission.

Solution
ApplyPilot is a semi-automated AI Job Application Copilot.

It does not simply spam applications. It:

Finds jobs based on the user’s preferences.

Scores each job against the user’s profile.

Generates a tailored resume and cover letter using only real user information.

Prefills application forms.

Sends applications to a review queue.

Submits only after user approval or according to strict user-configured rules.

Tracks application status and follow-ups.

Core Features
1. Profile Builder
Users can create a structured career profile:

Personal details and contact information

Resume upload and parsing

Work experience

Education

Skills and tools

Projects and portfolio links

LinkedIn / GitHub / website links

Work authorization and notice period

Expected salary

Preferred locations and remote preference

2. Job Preferences
Users define their target search:

Job titles

Industries

Locations

Remote / hybrid / onsite

Experience level

Salary range

Company size

Excluded companies

Daily application limit

Minimum match score

3. Job Discovery
The platform collects jobs from permitted sources:

Official job APIs

ATS job boards such as Greenhouse, Lever, Ashby, and Workday

Company career pages

Aggregator APIs

Manually saved jobs

Each job is stored with:

Title

Company

Location

Job description

Salary, if available

Source

Application URL

Posted date

4. AI Job Matching
For every new job, the AI compares the job description with the user profile and returns:

Match score from 0 to 100

Apply / Review / Skip recommendation

Reasons for fit

Missing skills

Resume focus areas

Risk flags, such as experience mismatch

Example output:

json
{
  "match_score": 84,
  "decision": "apply",
  "fit_reasons": [
    "Digital marketing experience",
    "SEO and content strategy overlap",
    "AI automation project experience"
  ],
  "missing_skills": ["HubSpot certification"],
  "resume_focus": [
    "SEO growth results",
    "AI workflow automation",
    "Website and campaign optimization"
  ],
  "risk_flags": []
}
5. AI Resume and Cover Letter Tailoring
For high-fit jobs, ApplyPilot creates:

A job-specific resume

A short cover letter

Suggested answers for common screening questions

Rules:

Use only facts from the user’s master profile.

Never invent experience, tools, companies, metrics, or dates.

Reorder and emphasize relevant achievements.

Mirror important job-description keywords truthfully.

Maintain a version history for every generated resume.

6. Application Autofill
A Chrome extension and browser automation layer can fill common application fields:

Name

Email

Phone number

LinkedIn profile

Portfolio / GitHub

Current company

Years of experience

Expected salary

Notice period

Work authorization

Resume upload

Cover letter upload

Screening questions

Supported initial ATS targets:

Greenhouse

Lever

Ashby

Workday

SmartRecruiters

Company career pages

7. Review Queue
Every application enters a review state before submission.

The user can:

Review the job

Check the match score

Edit the tailored resume

Edit the cover letter

Review AI-generated answers

Approve or reject the application

Submit manually or approve one application at a time

8. Application Tracker
Users can track every application:

Company and role

Job source

Application URL

Resume version used

Match score

Status

Applied date

Follow-up date

Interview notes

Rejection reason, if available

Application statuses:

Draft

Ready for review

Submitted

Screening

Interview

Offer

Rejected

Withdrawn

9. Notifications
Users receive:

Daily job-match digest

Applications ready for review

Submission confirmations

Follow-up reminders

Interview reminders

10. Analytics
The dashboard shows:

Applications submitted

Interview conversion rate

Best-performing job sources

Best-performing resume versions

Roles and locations with the highest response rate

Average match score of interviewed roles

Tech Stack
Frontend
Next.js

React

Tailwind CSS

shadcn/ui

Chrome Extension using Manifest V3

Backend
Node.js with Next.js API routes, or Python FastAPI

Supabase for authentication, PostgreSQL database, and file storage

Redis + BullMQ for job queues and scheduled workflows

Playwright for browser automation

Gemini API for matching, resume tailoring, and answer generation

Job Data
Start with structured and permitted sources:

Adzuna API

Greenhouse Job Board API

Arbeitnow API

Company career pages

User-saved job URLs

Infrastructure
Vercel for web app hosting

Supabase for database and auth

Railway, Render, or Fly.io for background workers

Cloud storage for resumes and generated PDFs

Razorpay or Stripe for payments

System Architecture
text
Web Dashboard / Chrome Extension
              |
              v
        API Backend
              |
    +---------+----------+
    |                    |
Job Ingestion       User Profile
    |                    |
Job Normalizer      Resume Parser
    |                    |
Matching Engine <--------+
    |
AI Document Generator
    |
Review Queue
    |
Application Automation Service
    |
Submission Worker
    |
Application Tracker + Notifications
Database Schema
users
id

email

full_name

created_at

profiles
id

user_id

phone

linkedin_url

portfolio_url

github_url

current_company

years_of_experience

expected_salary

notice_period

work_authorization

resume_file_url

job_preferences
id

user_id

target_roles

locations

work_type

experience_level

salary_min

salary_max

excluded_companies

daily_application_limit

minimum_match_score

jobs
id

source

external_job_id

title

company

location

work_type

description

salary_min

salary_max

application_url

posted_at

created_at

job_matches
id

user_id

job_id

match_score

decision

fit_reasons

missing_skills

resume_focus

risk_flags

created_at

resume_versions
id

user_id

job_id

file_url

generated_at

is_approved

cover_letters
id

user_id

job_id

content

file_url

created_at

applications
id

user_id

job_id

resume_version_id

status

application_url

match_score

submitted_at

follow_up_at

notes

application_events
id

application_id

event_type

message

created_at

User Flow
User signs up.

User uploads a resume or builds a profile manually.

User sets job preferences.

ApplyPilot fetches new jobs.

AI scores jobs and shows the best matches.

User selects jobs to apply to.

AI generates a tailored resume and cover letter.

User reviews and edits the documents.

ApplyPilot prefills the application form.

User reviews the final application.

User approves submission.

ApplyPilot tracks the application and sends follow-up reminders.

MVP Scope
Version 1 — Personal MVP
Manual resume upload

Job URL input

AI job-fit scoring

Tailored resume and cover letter

PDF generation

Basic application tracker

Google Sheets or Supabase storage

Version 2 — Public Beta
User authentication

Job preferences

Automated job ingestion

Match dashboard

Resume version history

Chrome extension autofill

Review queue

Email notifications

Version 3 — Paid Product
Subscription plans

Application credits

ATS-specific autofill adapters

Assisted auto-apply with approval

Analytics dashboard

Interview preparation module

Referral outreach drafts

Monetization
Plan	Price Idea	Includes
Free	₹0	Profile, limited job matches, basic resume builder, manual autofill
Starter	₹499–₹799/month	100 job matches, 10 tailored resumes, 20 autofills
Pro	₹1,499–₹1,999/month	Unlimited matches, 50 tailored applications, priority processing
Credits	₹10–₹25/application	Auto-apply submissions or premium tailoring
Career Coach	₹4,999+/month	Multi-candidate dashboard, branding, analytics
Revenue model:

Monthly subscription for core tools

Credit packs for application volume

Premium add-ons for interview prep and outreach

Future B2B plan for career coaches and institutes

Safety and Compliance
Do not automate LinkedIn applications or scraping.

Use official APIs and permitted job-data providers.

Require user approval before submission by default.

Apply daily limits to prevent spam-like behavior.

Never generate false work history, skills, certifications, or metrics.

Store user resumes securely and allow deletion.

Clearly disclose AI-generated content.

Respect each job board’s terms of service and robots policies.

Competitive Positioning
Product	Focus
AIApply	Job matching, tailored documents, auto-apply credits
JobCopilot	Daily automated applications from company career pages
Simplify	Job matching, resume customization, autofill
ApplyPilot	Controlled AI application workflow with strong matching, tailoring, review, and tracking
ApplyPilot’s differentiation:

Better job-fit explanations

Truthful, high-quality resume tailoring

Human-approved submissions by default

Strong application tracking and analytics

India-first focus for digital, tech, product, and growth roles

Development Roadmap
Phase 1: Foundation
Next.js app setup

Supabase authentication

Resume upload

Profile builder

Job preference form

Phase 2: AI Engine
Resume parsing

Job matching

Resume tailoring

Cover-letter generation

PDF export

Phase 3: Job Sources
Adzuna integration

Greenhouse integration

Job ingestion scheduler

Duplicate-job detection

Phase 4: Chrome Extension
Profile autofill

Field detection

Resume upload helper

Application logging

Phase 5: Product Launch
Payments

Free-plan limits

Onboarding

Landing page

Beta user feedback

Analytics

Success Metrics
Weekly active users

Jobs matched per user

Resume tailoring acceptance rate

Applications submitted

Interview conversion rate

Time saved per application

Free-to-paid conversion rate

Monthly recurring revenue

Churn rate

Future Features
AI interview preparation

Company research summaries

Referral-message generator

LinkedIn profile optimization suggestions

Resume score against ATS keywords

Job-alert automation

Mobile app

Career-coach dashboard

Multilingual support for Indian users

Resume A/B testing

Getting Started
bash
git clone https://github.com/your-username/applypilot.git
cd applypilot
npm install
cp .env.example .env
npm run dev
Environment Variables
text
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
GEMINI_API_KEY=your_gemini_api_key
ADZUNA_API_KEY=your_adzuna_api_key
ADZUNA_API_ID=your_adzuna_api_id
RESEND_API_KEY=your_email_api_key
License
Proprietary. All rights reserved.
