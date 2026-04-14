"use client";

import { useQuery } from "@tanstack/react-query";
import { getUsers } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { cn } from "@repo/ui/lib/utils";

export default function UsersPage() {
    const { data: users, isLoading } = useQuery({
        queryKey: ["users"],
        queryFn: getUsers,
    });

    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
            </div>

            <div className="rounded-md border bg-white shadow">
                <div className="relative w-full overflow-auto">
                    <table className="w-full caption-bottom text-sm">
                        <thead className="[&_tr]:border-b">
                            <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Name</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Email</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Role</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Vendor</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Verified</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Last Login</th>
                            </tr>
                        </thead>
                        <tbody className="[&_tr:last-child]:border-0">
                            {users?.map((user: any) => (
                                <tr key={user.id} className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                    <td className="p-4 align-middle font-medium">
                                        {user.firstName} {user.lastName}
                                    </td>
                                    <td className="p-4 align-middle">{user.email}</td>
                                    <td className="p-4 align-middle capitalize">{user.role}</td>
                                    <td className="p-4 align-middle">
                                        <div className="flex items-center gap-2">
                                            <span>{user.vendor?.name || "—"}</span>
                                            {user.vendor?.status && (
                                                <span
                                                    className={cn(
                                                        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                                                        user.vendor.status === "ACTIVE"
                                                            ? "bg-green-100 text-green-800"
                                                            : "bg-yellow-100 text-yellow-800"
                                                    )}
                                                >
                                                    {user.vendor.status}
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="p-4 align-middle">
                                        <span
                                            className={cn(
                                                "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
                                                user.emailVerified
                                                    ? "bg-green-100 text-green-800"
                                                    : "bg-red-100 text-red-800"
                                            )}
                                        >
                                            {user.emailVerified ? "Verified" : "Unverified"}
                                        </span>
                                    </td>
                                    <td className="p-4 align-middle text-sm text-muted-foreground">
                                        {user.lastLoginAt
                                            ? new Date(user.lastLoginAt).toLocaleDateString()
                                            : "Never"}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
