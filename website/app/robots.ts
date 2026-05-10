import type { MetadataRoute } from "next";

const SITE_URL = "https://happycake.us";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Keep mutating/runtime APIs out of search indexing while leaving
        // the agent descriptor and llms.txt discoverable.
        disallow: ["/api/"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
