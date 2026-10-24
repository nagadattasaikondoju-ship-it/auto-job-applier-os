import type { Metadata, Viewport } from "next";
import "./globals.css";
import { JsonLd } from "@/components/seo/JsonLd";
import { landingContent } from "@/content/landing";

const siteUrl = landingContent.brand.url;

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#07070A" },
  ],
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Applyon — AI Job Applications for India | Tailor Resume & Autofill",
    template: "%s | Applyon",
  },
  description:
    "Applyon is your AI job search assistant for India. Find matching jobs, tailor an ATS-friendly resume, autofill applications and track every application in one dashboard.",
  applicationName: "Applyon",
  category: "Career",
  authors: [{ name: "Applyon Team" }],
  creator: "Applyon",
  publisher: "Applyon",
  keywords: [
    "AI job application India",
    "AI resume tailoring",
    "ATS friendly resume",
    "autofill job applications",
    "job search app India",
    "jobs for freshers",
    "cover letter generator",
    "job application tracker",
    "AI job search assistant",
    "how to tailor resume for each job",
    "how to get more interview calls",
    "best AI tool for job search in India",
    "apply for jobs faster",
    "resume for freshers in India",
  ],
  alternates: {
    canonical: "/",
    languages: {
      "en-IN": "/",
    },
  },
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: siteUrl,
    siteName: "Applyon",
    title: "Applyon — AI Job Applications for India | Tailor Resume & Autofill",
    description:
      "Applyon is your AI job search assistant for India. Find matching jobs, tailor an ATS-friendly resume, autofill applications and track every application in one dashboard.",
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "Applyon — AI Job Applications for India",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Applyon — AI Job Applications for India",
    description:
      "Find matching jobs, tailor an ATS-friendly resume, autofill applications and track every application in one dashboard.",
    images: ["/twitter-image"],
  },
  robots: {
    index: true,
    follow: true,
    "max-image-preview": "large",
    "max-snippet": -1,
  },
  manifest: "/manifest.webmanifest",
  verification: {
    google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION || undefined,
    other: process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION
      ? { "msvalidate.01": process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION }
      : undefined,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en-IN" suppressHydrationWarning>
      <head>
        <JsonLd />
      </head>
      <body className="antialiased selection:bg-indigo-500/20 selection:text-indigo-600 font-body">
        {children}
      </body>
    </html>
  );
}
