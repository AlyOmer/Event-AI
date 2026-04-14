"use client";

import { usePathname } from "next/navigation";
import { Navbar } from "./navbar";

const NO_NAV_ROUTES = ["/login", "/signup", "/register"];
// Pages that manage their own full-width layout
const FULL_WIDTH_ROUTES = ["/", "/chat"];

export function LayoutShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const showNav = !NO_NAV_ROUTES.includes(pathname);
    const isFullWidth = FULL_WIDTH_ROUTES.includes(pathname);

    return (
        <>
            {showNav && <Navbar />}
            {isFullWidth || !showNav ? (
                <>{children}</>
            ) : (
                <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
                    {children}
                </main>
            )}
        </>
    );
}
