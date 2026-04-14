import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "My Bookings | Event-AI",
    description: "View and manage your event service bookings on Event-AI.",
};

export default function BookingsLayout({ children }: { children: React.ReactNode }) {
    return children;
}
