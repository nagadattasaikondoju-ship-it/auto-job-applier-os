export interface FaqItem {
  question: string;
  answer: string;
  category: string;
}

export interface PricingPlan {
  name: string;
  price: string;
  yearlyPrice: string;
  billingPeriod: string;
  originalPrice?: string;
  description: string;
  features: { text: string; included: boolean }[];
  featured?: boolean;
  badge?: string;
  bg: string;
}

export interface CreditPack {
  credits: number;
  price: string;
  pricePerApp: string;
  badge?: string;
  popular?: boolean;
}

export interface Testimonial {
  name: string;
  role: string;
  city: string;
  quote: string;
  avatar: string;
}

export interface ComparisonRow {
  criterion: string;
  manual: { value: string; label: string };
  bots: { value: string; label: string };
  applyon: { value: string; label: string };
}

export const landingContent = {
  brand: {
    name: "Applyon",
    tagline: "Apply smarter. Interview sooner.",
    description:
      "Applyon is your AI job search assistant for India. Find matching jobs, tailor an ATS-friendly resume, autofill applications and track every application in one dashboard.",
    url: process.env.NEXT_PUBLIC_SITE_URL || "https://applyon.ai",
    category: "Career",
    socialLinks: [] as string[],
  },
  hero: {
    eyebrow: "AI-powered job applications for India",
    titleLine1: "Apply smarter.",
    titleLine2: "Interview sooner.",
    subtext:
      "AI-powered job applications for India's next generation of professionals. Discover matching roles, tailor your resume, autofill applications, and manage your job hunt from one dashboard.",
    cta: "Join the waitlist",
    inputPlaceholder: "Enter your work or personal email...",
    badge: "✦ Now with GPT-5 support & verified India tech salary benchmarks ✨",
    dashboardFigcaption:
      "Applyon dashboard showing a 92% job fit score, tailored resume and autofilled application for Indian tech roles",
  },
  trust: {
    heading: "Built for job seekers targeting India's top startups and tech companies",
    companies: [
      "RAZORFIN",
      "HYPERGROWTH",
      "LATTICE OS",
      "NOVAPAY",
      "ZEPTH AI",
      "KINETIX",
      "VERTEX LABS",
      "SCALEFORGE",
      "FINWAVE",
      "SYNERGY CLOUD",
    ],
  },
  problem: {
    heading: "Job hunting is broken.",
    subheading:
      "Why applying to hundreds of jobs with one resume doesn't get you interview calls.",
    stats: [
      {
        value: "4+ hrs",
        label: "Lost to repetitive forms every day",
        description:
          "Filling duplicate work history, CTC expectations, and manual dropdowns across dozens of workday, lever and greenhouse portals.",
      },
      {
        value: "100+",
        label: "Applications before one interview",
        description:
          "Applying blindly without an ATS friendly resume causes qualified candidates to be silently filtered out by applicant tracking bots.",
      },
      {
        value: "1 resume",
        label: "Sent to every job, unchanged",
        description:
          "Without automated AI resume tailoring, recruiters never see how your specific achievements match their requirements.",
      },
    ],
    closingQuote:
      "You don't need to apply to more jobs. You need to apply to the right ones — with the right resume.",
  },
  howItWorks: {
    heading: "How Applyon works: from resume to interview in four steps",
    subheading:
      "From resume upload to signed offer letter: our AI job search assistant automates tedious paperwork while leaving final control in your hands.",
    steps: [
      {
        number: "01",
        title: "Upload your resume",
        description:
          "Upload your existing CV (PDF/DOCX). Our AI parses your career history, skills, and metrics into a verified master career profile in seconds.",
        keyword: "upload your resume",
      },
      {
        number: "02",
        title: "Discover matching roles",
        description:
          "Explore curated roles across Bengaluru, Hyderabad, Pune, Mumbai and Delhi NCR. Each job is scored by fit score with matched and missing skills explained.",
        keyword: "job search app India",
      },
      {
        number: "03",
        title: "AI resume tailoring & autofill",
        description:
          "Generate an ATS friendly resume tailored to each role using strictly your genuine background, then autofill job applications in one click.",
        keyword: "AI resume tailoring",
      },
      {
        number: "04",
        title: "Review, approve & track",
        description:
          "Approve every submission with your built-in job application tracker. Stay organized with real-time status updates and automated follow-up reminders.",
        keyword: "job application tracker",
      },
    ],
  },
  features: {
    heading: "Your whole job hunt, one dashboard.",
    subheading:
      "Six purpose-built AI tools designed for students, freshers, and experienced engineers across India.",
    cards: [
      {
        title: "Smart job matching",
        keyword: "Smart job matching",
        description: "Matching roles ranked by fit score across Bengaluru, Pune, Hyderabad and remote India.",
      },
      {
        title: "AI resume tailoring",
        keyword: "AI resume tailoring",
        description: "ATS-friendly resume for every job, rephrasing your truthful achievements without fabricating experience.",
      },
      {
        title: "One-click autofill",
        keyword: "One-click autofill",
        description: "Autofill job applications in 3 seconds across complex portals; you review and approve before submission.",
      },
      {
        title: "Cover letter generator",
        keyword: "Cover letter generator",
        description: "Personalized, concise cover letters tailored to each company's mission and team culture in seconds.",
      },
      {
        title: "Job application tracker",
        keyword: "Job application tracker",
        description: "Kanban board tracking every application status, interview round, CTC discussion, and follow-up deadline.",
      },
      {
        title: "Fit score insights",
        keyword: "Fit score insights",
        description: "Transparent percentage score explaining exactly which requirements match your profile and which skills to brush up on.",
      },
    ],
  },
  safety: {
    heading: "AI that works for you — not around you.",
    subheading:
      "We guarantee a truthful resume, no spam bots, and strict candidate data privacy. Your personal information is encrypted and never sold.",
    promises: [
      {
        title: "No fake experience. Ever.",
        description: "Tailoring only rephrases and reorders your genuine achievements. Never invents roles or credentials.",
      },
      {
        title: "No spam bots.",
        description: "We never mass-spray unvetted applications or automate sites that forbid bot submissions.",
      },
      {
        title: "You approve every application.",
        description: "Autofill prepares the form accurately; you review and approve every single application before it is submitted.",
      },
    ],
  },
  comparison: {
    heading: "Applyon vs auto-apply bots vs manual applying",
    caption: "Detailed comparison of job application approaches in the Indian tech job market",
    rows: [
      {
        criterion: "Tailored per job",
        manual: { value: "Rarely (takes hours)", label: "Partial" },
        bots: { value: "Generic / Broken", label: "No" },
        applyon: { value: "Instant & ATS-Optimized", label: "Yes" },
      },
      {
        criterion: "Truthful resume",
        manual: { value: "100% Truthful", label: "Yes" },
        bots: { value: "Hallucinates experience", label: "No" },
        applyon: { value: "100% Real experience only", label: "Yes" },
      },
      {
        criterion: "Forms filled for you",
        manual: { value: "None (Manual retyping)", label: "No" },
        bots: { value: "Prone to submission errors", label: "Partial" },
        applyon: { value: "One-click accurate autofill", label: "Yes" },
      },
      {
        criterion: "You stay in control",
        manual: { value: "Full control (High fatigue)", label: "Yes" },
        bots: { value: "Zero control (Ghosted)", label: "No" },
        applyon: { value: "Mandatory human review", label: "Yes" },
      },
      {
        criterion: "Time saved per week",
        manual: { value: "0 hrs (High burnout)", label: "No" },
        bots: { value: "High (Spams junk)", label: "Partial" },
        applyon: { value: "15+ hours saved", label: "Yes" },
      },
      {
        criterion: "Interview callback quality",
        manual: { value: "Low volume", label: "Partial" },
        bots: { value: "Blacklisted by ATS", label: "No" },
        applyon: { value: "3.4x higher callback rate", label: "Yes" },
      },
    ] as ComparisonRow[],
  },
  testimonials: {
    heading: "What early users say about Applyon",
    subheading: "Trusted by students, freshers, and experienced software engineers landing top tech roles across India.",
    items: [
      {
        name: "Priya S.",
        role: "Data Analyst",
        city: "Pune",
        quote: "Applying to 50+ roles used to take all weekend. With Applyon, my resume was tailored to each job description, and I landed 4 interview calls within 10 days.",
        avatar: "PS",
      },
      {
        name: "Arjun R.",
        role: "SDE-1",
        city: "Bengaluru",
        quote: "The autofill feature saved me countless hours on Workday portals. Best part: the AI never invented fake skills on my resume.",
        avatar: "AR",
      },
      {
        name: "Sneha K.",
        role: "Frontend Fresher",
        city: "Hyderabad",
        quote: "As a 2026 grad, competing with thousands of applicants was discouraging. Applyon's fit score helped me target the exact roles where my skills stood out.",
        avatar: "SK",
      },
      {
        name: "Rohan M.",
        role: "Product Designer",
        city: "Mumbai",
        quote: "The visual job application tracker keeps my job search organized. I know exactly when to follow up and what version of my resume was sent.",
        avatar: "RM",
      },
      {
        name: "Ananya D.",
        role: "QA Automation Engineer",
        city: "Chennai",
        quote: "A game changer for India tech hiring. No spam, just high-relevance applications that actually get noticed by hiring managers.",
        avatar: "AD",
      },
    ] as Testimonial[],
  },
  // Hybrid Monetization Model: Toolkit Subscriptions + Application Volume Credits
  pricing: [
    {
      name: "Free",
      price: "0",
      yearlyPrice: "0",
      billingPeriod: "/forever",
      originalPrice: "499",
      description: "Profile, 10 job matches/week, basic resume, manual autofill.",
      bg: "#141416",
      features: [
        { text: "Master candidate profile", included: true },
        { text: "10 job matches per week", included: true },
        { text: "Basic ATS resume export", included: true },
        { text: "Manual autofill helper", included: true },
        { text: "Priority submission queue", included: false },
      ],
    },
    {
      name: "Starter",
      price: "499",
      yearlyPrice: "399",
      billingPeriod: "/month",
      originalPrice: "799",
      description: "100 matches, 10 tailored resumes, 20 autofills.",
      bg: "#1C1C20",
      features: [
        { text: "100 curated tech job matches", included: true },
        { text: "10 AI tailored resumes", included: true },
        { text: "20 verified portal autofills", included: true },
        { text: "ATS friendly PDF/Word export", included: true },
        { text: "Multi-candidate dashboard", included: false },
      ],
    },
    {
      name: "Pro",
      price: "1499",
      yearlyPrice: "1199",
      billingPeriod: "/month",
      originalPrice: "1999",
      description: "Unlimited matches, 50 tailored applications, priority queue.",
      bg: "#25252B",
      featured: true,
      badge: "Best Value",
      features: [
        { text: "Unlimited smart job matches", included: true },
        { text: "50 tailored applications/month", included: true },
        { text: "Unlimited portal autofill", included: true },
        { text: "Priority review queue & support", included: true },
        { text: "AI cover letter generator", included: true },
      ],
    },
    {
      name: "Career Coach",
      price: "4999",
      yearlyPrice: "3999",
      billingPeriod: "/month",
      originalPrice: "6999",
      description: "Multi-candidate dashboard, branding, analytics for placement cells & coaches.",
      bg: "#17181D",
      features: [
        { text: "Multi-candidate management dashboard", included: true },
        { text: "Custom agency & placement branding", included: true },
        { text: "Batch candidate analytics & ATS reports", included: true },
        { text: "Shared placement tracking pipeline", included: true },
        { text: "Dedicated placement account manager", included: true },
      ],
    },
  ] as PricingPlan[],
  credits: {
    heading: "Auto Apply Credit Packs",
    subheading:
      "Pay-as-you-go volume packs. One credit equals one verified application submission or premium tailoring.",
    unitRange: "₹10–₹25 / application",
    packs: [
      {
        credits: 20,
        price: "499",
        pricePerApp: "₹25/app",
        badge: "Test Drive",
        popular: false,
      },
      {
        credits: 50,
        price: "899",
        pricePerApp: "₹18/app",
        badge: "Most Popular",
        popular: true,
      },
      {
        credits: 120,
        price: "1499",
        pricePerApp: "₹12.5/app",
        badge: "Best Value",
        popular: false,
      },
      {
        credits: 300,
        price: "2999",
        pricePerApp: "₹10/app",
        badge: "Max Volume",
        popular: false,
      },
    ] as CreditPack[],
  },
  finalCta: {
    heading: "Your next interview is one great application away.",
    subheading: "Join the Applyon waitlist — free during beta for job seekers across India. No credit card required.",
    cta: "Join priority waitlist",
  },
  faqs: [
    {
      question: "How does the hybrid subscription and credits model work?",
      answer:
        "Applyon uses a transparent hybrid model inspired by top global tools: subscriptions cover your core copilot toolkit (dashboard, job search matching, profile tracking), while Auto Apply credits give you pay-as-you-go flexibility for application submissions (₹10–₹25 per application). One credit equals one verified application submission or premium tailoring, with credits that never expire.",
      category: "Pricing & Plans",
    },
    {
      question: "What is the best AI tool for job search in India?",
      answer:
        "Applyon is built specifically as the best AI tool for job search in India. Unlike spammy auto-apply bots, Applyon is an AI job copilot that scores roles against your profile, crafts tailored ATS-friendly resumes using only your real experience, prefills portal forms, and gives you total approval before submission.",
      category: "Platform",
    },
    {
      question: "How do I tailor my resume for each job?",
      answer:
        "To tailor your resume for each job, Applyon analyzes the target job description, extracts required competencies, and aligns your truthful experience to highlight matching achievements. This produces a keyword-optimized, ATS-friendly resume that passes screening filters without inventing facts.",
      category: "Resume Tailoring",
    },
    {
      question: "Is Applyon free for freshers and students?",
      answer:
        "Yes, Applyon offers a 100% free plan for freshers, students, and early-career job seekers across India. The Free tier includes a master candidate profile, 10 job matches per week, basic resume export, and our manual autofill helper.",
      category: "Pricing & Plans",
    },
    {
      question: "Does Applyon make my resume ATS friendly?",
      answer:
        "Yes, every resume generated by Applyon follows clean ATS-compliant formatting standards: single-column structure, standard section headers, parseable typography, and semantic keyword matching tailored to the employer's applicant tracking system.",
      category: "Resume Tailoring",
    },
    {
      question: "How does Applyon help me get more interview calls?",
      answer:
        "Applyon helps you get more interview calls by ensuring you apply only to high-fit roles with resumes customized to the hiring team's exact requirements. By eliminating irrelevant applications and highlighting truthful impact metrics, users see an average 3.4x boost in interview callbacks.",
      category: "Career Growth",
    },
    {
      question: "What assets can I trade on ZENTRADE?",
      answer:
        "Forex majors and minors, indices, commodities such as gold and oil, and popular cryptocurrencies, all from one account, with live spread, leverage and trading hours transparently displayed before each order is placed.",
      category: "Trading & Markets",
    },
    {
      question: "What is ZENTRADE?",
      answer:
        "ZENTRADE is an online trading platform providing institutional and retail traders seamless access to global financial markets through a low-latency, secure web interface with dedicated 24/7 client support.",
      category: "Trading & Markets",
    },
  ] as FaqItem[],
};
