import type { MetadataRoute } from "next";
import { landingContent } from "@/content/landing";

/**
 * Sitemap configuration for Applyon
 *
 * HOW TO ADD NEW PAGES:
 * 1. Add the path to the `routes` array below with appropriate changeFrequency and priority.
 * 2. Ensure the corresponding page in `src/app/<route>/page.tsx` exists with unique metadata and canonical URLs.
 * 3. Run `npm run build` to verify the generated sitemap.xml.
 */

export default function sitemap(): MetadataRoute.Sitemap {
  const siteUrl = landingContent.brand.url;
  const currentDate = new Date().toISOString();

  const routes: {
    path: string;
    priority: number;
    changeFrequency: "always" | "hourly" | "daily" | "weekly" | "monthly" | "yearly" | "never";
  }[] = [
    { path: "", priority: 1.0, changeFrequency: "daily" },
    { path: "/resume-tailoring", priority: 0.8, changeFrequency: "weekly" },
    { path: "/autofill-job-applications", priority: 0.8, changeFrequency: "weekly" },
    { path: "/jobs-for-freshers", priority: 0.8, changeFrequency: "weekly" },
    { path: "/blog", priority: 0.7, changeFrequency: "weekly" },
    { path: "/privacy", priority: 0.3, changeFrequency: "yearly" },
    { path: "/terms", priority: 0.3, changeFrequency: "yearly" },
  ];

  return routes.map((route) => ({
    url: `${siteUrl}${route.path}`,
    lastModified: currentDate,
    changeFrequency: route.changeFrequency,
    priority: route.priority,
  }));
}
