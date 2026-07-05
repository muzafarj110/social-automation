// Shared pricing/tier data used by Billing.jsx and Landing.jsx.
// Keep this file as the single source of truth — update both consumers by editing here.

export const TIER_ORDER = ["free", "starter", "growth", "pro"];

export const TIER_DATA = {
  free: {
    price: "$0",
    label: "Free",
    note: "30 credits/day, no card needed",
    included: [
      "30 credits / day — no card needed",
      "Quick post generator (1 cr)",
      "Content agent drafts (1 cr)",
      "Competitor analysis (1 cr)",
      "Social listening scans (1 cr)",
      "Lead-gen outreach drafts (1 cr)",
      "Opportunities refresh (1 cr)",
      "WhatsApp + Telegram cross-posting",
      "Post calendar and scheduling",
    ],
    excluded: [
      "Always-on Campaigns",
      "Studio images (5 cr each)",
      "SEO + GEO deep analysis (2 cr)",
    ],
  },
  starter: {
    price: "$29",
    label: "Starter",
    note: "for getting serious",
    included: [
      "Content agent — drafts and posts",
      "Quick post generator",
      "Competitor agent (1 rival)",
      "Post calendar",
      "WhatsApp + Telegram cross-posting",
    ],
    excluded: [
      "Always-on Campaigns",
      "SEO + GEO agent",
      "Studio images and carousels",
    ],
  },
  growth: {
    price: "$79",
    label: "Growth",
    note: "for growing teams",
    popular: true,
    included: [
      "Everything in Starter",
      "Always-on Campaigns — set and forget posting",
      "SEO + GEO agent",
      "Social listening agent",
      "Lead-gen agent",
      "Opportunities agent",
    ],
    excluded: [
      "Studio agent (images, carousels)",
      "Multi-client workspaces",
    ],
  },
  pro: {
    price: "$149",
    label: "Pro",
    note: "for full automation",
    included: [
      "Everything in Growth",
      "Studio agent — images, carousels, newsletters",
      "Brand strategist agent",
      "Multi-client workspaces",
      "Unlimited competitor tracking",
      "Priority support",
      "Credit top-ups available",
    ],
    excluded: [],
  },
};
