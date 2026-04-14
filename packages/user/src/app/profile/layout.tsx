import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "My Profile | Event-AI",
    description: "Manage your Event-AI account, update personal information, and change your password.",
};

export default function ProfileLayout({ children }: { children: React.ReactNode }) {
    return children;
}
