import type { MetadataRoute } from "next";

const SITE_URL = "https://happycake.us";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Block agent endpoints from being indexed by search engines
        // (they're for runtime AI agents, not SEO).
        disallow: ["/api/", "/agent.json"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
