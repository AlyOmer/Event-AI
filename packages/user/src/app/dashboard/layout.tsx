import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "My Dashboard | Event-AI",
    description: "View your events, bookings, and plan your next celebration with Event-AI's smart event planning tools.",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    return children;
}
