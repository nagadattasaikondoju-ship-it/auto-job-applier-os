import type { MetadataRoute } from "next";
import { landingContent } from "@/content/landing";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Applyon — AI Job Applications for India",
    short_name: landingContent.brand.name,
    description: landingContent.brand.description,
    start_url: "/",
    display: "standalone",
    background_color: "#07070A",
    theme_color: "#07070A",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
      },
    ],
  };
}
