import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Vendor Details | Event-AI",
    description: "View vendor services, ratings, and book event services on Event-AI.",
};

export default function VendorLayout({ children }: { children: React.ReactNode }) {
    return children;
}
