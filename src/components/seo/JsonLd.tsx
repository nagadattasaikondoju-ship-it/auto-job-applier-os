import React from "react";
import { landingContent } from "@/content/landing";

export function JsonLd() {
  const siteUrl = landingContent.brand.url;

  // 1. Organization
  const organizationSchema = {
    "@type": "Organization",
    "@id": `${siteUrl}#organization`,
    name: landingContent.brand.name,
    url: siteUrl,
    logo: `${siteUrl}/icon.svg`,
    description: landingContent.brand.description,
    sameAs: landingContent.brand.socialLinks,
  };

  // 2. WebSite
  const websiteSchema = {
    "@type": "WebSite",
    "@id": `${siteUrl}#website`,
    name: landingContent.brand.name,
    url: siteUrl,
    inLanguage: "en-IN",
    publisher: {
      "@id": `${siteUrl}#organization`,
    },
  };

  // 3. SoftwareApplication
  const softwareApplicationSchema = {
    "@type": "SoftwareApplication",
    "@id": `${siteUrl}#software`,
    name: landingContent.brand.name,
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    description: landingContent.brand.description,
    offers: [
      ...landingContent.pricing.map((plan) => ({
        "@type": "Offer",
        name: plan.name,
        price: plan.price,
        priceCurrency: "INR",
        priceValidUntil: "2027-12-31",
        availability: "https://schema.org/InStock",
        url: `${siteUrl}#pricing`,
      })),
      {
        "@type": "Offer",
        name: "Auto Apply Credit Pack (20 Applications)",
        price: "499",
        priceCurrency: "INR",
        priceValidUntil: "2027-12-31",
        availability: "https://schema.org/InStock",
        url: `${siteUrl}#pricing`,
      },
    ],
  };

  // 4. FAQPage
  const faqSchema = {
    "@type": "FAQPage",
    "@id": `${siteUrl}#faq`,
    mainEntity: landingContent.faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };

  // 5. BreadcrumbList
  const breadcrumbSchema = {
    "@type": "BreadcrumbList",
    "@id": `${siteUrl}#breadcrumb`,
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: siteUrl,
      },
    ],
  };

  const schemaGraph = {
    "@context": "https://schema.org",
    "@graph": [
      organizationSchema,
      websiteSchema,
      softwareApplicationSchema,
      faqSchema,
      breadcrumbSchema,
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaGraph) }}
    />
  );
}
