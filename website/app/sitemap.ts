import type { MetadataRoute } from "next";
import { loadCatalog } from "@/lib/catalog";

const SITE_URL = "https://happycake.us";

export default function sitemap(): MetadataRoute.Sitemap {
  const catalog = loadCatalog();
  const lastModified = new Date(catalog.capturedAt);

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, lastModified, changeFrequency: "daily", priority: 1.0 },
    { url: `${SITE_URL}/menu`, lastModified, changeFrequency: "daily", priority: 0.9 },
    { url: `${SITE_URL}/about`, lastModified, changeFrequency: "monthly", priority: 0.6 },
    { url: `${SITE_URL}/policies`, lastModified, changeFrequency: "monthly", priority: 0.5 },
  ];

  const productRoutes: MetadataRoute.Sitemap = catalog.items.map((item) => ({
    url: `${SITE_URL}/p/${item.slug}`,
    lastModified,
    changeFrequency: "weekly" as const,
    priority: 0.8,
  }));

  return [...staticRoutes, ...productRoutes];
}
