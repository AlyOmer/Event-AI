"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "./sidebar";

const NO_SIDEBAR_ROUTES = ["/login"];

export function LayoutShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const showSidebar = !NO_SIDEBAR_ROUTES.includes(pathname);

    if (!showSidebar) {
        return <>{children}</>;
    }

    return (
        <>
            <Sidebar />
            <main className="flex-1 overflow-y-auto bg-gray-50/50">
                <div className="p-8">
                    {children}
                </div>
            </main>
        </>
    );
}
