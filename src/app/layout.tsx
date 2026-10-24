import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Applyon — AI-Powered Job Applications for India",
  description:
    "AI-powered job applications for India's next generation of professionals. Discover matching roles, tailor your resume, autofill applications, and manage your job hunt from one dashboard.",
  keywords: [
    "AI job application India",
    "resume tailoring",
    "job search India",
    "autofill job applications",
    "fresher jobs",
    "Applyon",
    "AI job copilot",
  ],
  authors: [{ name: "Applyon Team" }],
  creator: "Applyon",
  publisher: "Applyon Inc.",
  metadataBase: new URL("https://applyon.ai"),
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: "https://applyon.ai",
    title: "Applyon — Apply smarter. Interview sooner.",
    description:
      "Automate your busywork with intelligent agents that learn, adapt, and execute—so your team can focus on what matters most.",
    siteName: "Applyon",
  },
  twitter: {
    card: "summary_large_image",
    title: "Applyon — AI Job Application Copilot",
    description: "Apply smarter. Interview sooner.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Applyon",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "INR",
    },
    description:
      "AI-powered job application copilot for discovering roles, tailoring resumes, and autofilling applications.",
  };

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="antialiased selection:bg-indigo-500/20 selection:text-indigo-600">
        {children}
      </body>
    </html>
  );
}
