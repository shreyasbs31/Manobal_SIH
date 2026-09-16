import { ComponentGallery } from "@manobal/ui";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { isDemoMode } from "@/lib/mode";

export const metadata: Metadata = { title: "Component gallery" };

export default function GalleryPage() {
  if (!isDemoMode()) {
    notFound();
  }
  return <ComponentGallery />;
}
