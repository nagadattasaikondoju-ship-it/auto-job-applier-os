import type { MetadataRoute } from "next";
import { landingContent } from "@/content/landing";

export default function robots(): MetadataRoute.Robots {
  const siteUrl = landingContent.brand.url;
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/"],
    },
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
