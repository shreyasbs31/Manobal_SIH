import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "MANOBAL Saathi",
    short_name: "Saathi",
    description: "Private daily support. Support, not surveillance.",
    start_url: "/app",
    display: "standalone",
    background_color: "#F5F8F7",
    theme_color: "#2F5D50",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
