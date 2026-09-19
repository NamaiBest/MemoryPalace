import type { MomentMedia } from "@/types/moment";

// Local placeholder scenes so the prototype renders with no network. Real POV
// media will arrive from the backend via resolveCameraSource / loadMoments.
export const MEDIA = {
  desk: {
    thumbnailUrl: "/media/desk.svg",
    alt: "Lit desk with a monitor of dense text",
  },
  city: {
    thumbnailUrl: "/media/city.svg",
    alt: "City skyline at dusk",
  },
  night: {
    thumbnailUrl: "/media/night.svg",
    alt: "Moonlit ridgeline under stars",
  },
  study: {
    thumbnailUrl: "/media/study.svg",
    alt: "Library shelves beside a lamp and open book",
  },
  train: {
    thumbnailUrl: "/media/train.svg",
    alt: "Landscape blurring past a train window",
  },
  cafe: {
    thumbnailUrl: "/media/cafe.svg",
    alt: "Cafe table with a cup and books under warm lights",
  },
} satisfies Record<string, MomentMedia>;
