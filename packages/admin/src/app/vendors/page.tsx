"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getVendors, updateVendorStatus } from "@/lib/api";
import { Check, X, Loader2, ChevronLeft, ChevronRight, Store, Search } from "lucide-react";
import { cn } from "@repo/ui/lib/utils";
import { useState } from "react";

export default function VendorsPage() {
    const queryClient = useQueryClient();
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const PAGE_SIZE = 10;

    const { data: vendors, isLoading } = useQuery({
        queryKey: ["vendors"],
        queryFn: getVendors,
    });

    const allVendors: any[] = (vendors || []).filter((v: any) =>
        !search || v.name?.toLowerCase().includes(search.toLowerCase())
    );
    const totalPages = Math.max(1, Math.ceil(allVendors.length / PAGE_SIZE));
    const paginatedVendors = allVendors.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

    const mutation = useMutation({
        mutationFn: ({ id, status }: { id: string; status: string }) =>
            updateVendorStatus(id, status),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vendors"] }),
    });

    if (isLoading) {
        return (
            <div className="space-y-6">
                <div className="h-8 w-56 animate-pulse rounded-xl bg-gray-200" />
                <div className="rounded-2xl bg-white border border-gray-100 overflow-hidden">
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="flex items-center gap-4 px-6 py-4 border-b border-gray-50">
                            <div className="h-9 w-9 animate-pulse rounded-xl bg-gray-200" />
                            <div className="flex-1 space-y-2">
                                <div className="h-4 w-40 animate-pulse rounded bg-gray-200" />
                                <div className="h-3 w-24 animate-pulse rounded bg-gray-200" />
                            </div>
                            <div className="h-6 w-16 animate-pulse rounded-full bg-gray-200" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Vendor Management</h1>
                    <p className="mt-1 text-sm text-gray-500">{allVendors.length} vendors registered</p>
                </div>
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search vendors..."
                        value={search}
                        onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                        className="pl-9 pr-4 py-2 text-sm rounded-xl border border-gray-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-300 w-56"
                    />
                </div>
            </div>

            {/* Table */}
            <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="bg-gray-50/80 border-b border-gray-100">
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Vendor</th>
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Category</th>
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Status</th>
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Rating</th>
                            <th className="px-6 py-3.5 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                        {paginatedVendors.map((vendor: any) => (
                            <tr key={vendor.id} className="hover:bg-gray-50/50 transition-colors">
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-100 to-indigo-100 text-violet-600 text-xs font-bold">
                                            {vendor.name?.substring(0, 2).toUpperCase()}
                                        </div>
                                        <span className="font-medium text-gray-900">{vendor.name}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-gray-500 capitalize">{vendor.category}</td>
                                <td className="px-6 py-4">
                                    <span className={cn(
                                        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
                                        vendor.status === "ACTIVE"
                                            ? "bg-emerald-50 text-emerald-700"
                                            : vendor.status === "SUSPENDED" || vendor.status === "DEACTIVATED"
                                                ? "bg-red-50 text-red-700"
                                                : "bg-amber-50 text-amber-700"
                                    )}>
                                        {vendor.status}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-1">
                                        <span className="text-amber-400">★</span>
                                        <span className="text-gray-700 font-medium">{vendor.rating || "—"}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex justify-end gap-1.5">
                                        <button
                                            onClick={() => mutation.mutate({ id: vendor.id, status: "ACTIVE" })}
                                            disabled={vendor.status === "ACTIVE" || mutation.isPending}
                                            title="Approve"
                                            className="flex h-8 w-8 items-center justify-center rounded-lg text-emerald-600 hover:bg-emerald-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                        >
                                            <Check className="h-4 w-4" />
                                        </button>
                                        <button
                                            onClick={() => mutation.mutate({ id: vendor.id, status: "SUSPENDED" })}
                                            disabled={vendor.status === "SUSPENDED" || mutation.isPending}
                                            title="Suspend"
                                            className="flex h-8 w-8 items-center justify-center rounded-lg text-red-500 hover:bg-red-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                        >
                                            <X className="h-4 w-4" />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                        {paginatedVendors.length === 0 && (
                            <tr>
                                <td colSpan={5} className="px-6 py-16 text-center">
                                    <Store className="h-10 w-10 text-gray-200 mx-auto mb-3" />
                                    <p className="text-sm text-gray-400">No vendors found</p>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="flex items-center justify-between px-6 py-3.5 border-t border-gray-100 bg-gray-50/50">
                        <span className="text-xs text-gray-500">
                            Page {page} of {totalPages} · {allVendors.length} vendors
                        </span>
                        <div className="flex gap-1.5">
                            <button
                                onClick={() => setPage((p) => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                            >
                                <ChevronLeft className="h-3.5 w-3.5" /> Prev
                            </button>
                            <button
                                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                            >
                                Next <ChevronRight className="h-3.5 w-3.5" />
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
