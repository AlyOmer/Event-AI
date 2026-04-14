"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import {
    Users, Store, TrendingUp, Activity,
    AlertCircle, CheckCircle, XCircle, Loader2,
    ArrowUpRight, Clock,
} from "lucide-react";
import { getStats, getVendors, updateVendorStatus } from "@/lib/api";
import toast from "react-hot-toast";

export default function Dashboard() {
    const { data: session, status } = useSession();
    const router = useRouter();
    const queryClient = useQueryClient();
    const [actionVendorId, setActionVendorId] = useState<string | null>(null);

    useEffect(() => {
        if (status === "unauthenticated") router.push("/login");
    }, [status, router]);

    const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
        queryKey: ["stats"],
        queryFn: getStats,
    });

    const { data: recentVendors, isLoading: vendorsLoading } = useQuery({
        queryKey: ["recentVendors"],
        queryFn: getVendors,
    });

    const statusMutation = useMutation({
        mutationFn: ({ id, newStatus }: { id: string; newStatus: string }) =>
            updateVendorStatus(id, newStatus),
        onSuccess: (_, { newStatus }) => {
            toast.success(`Vendor ${newStatus === "ACTIVE" ? "approved" : "rejected"}`);
            queryClient.invalidateQueries({ queryKey: ["recentVendors"] });
            queryClient.invalidateQueries({ queryKey: ["stats"] });
            setActionVendorId(null);
        },
        onError: () => {
            toast.error("Failed to update vendor status");
            setActionVendorId(null);
        },
    });

    if (status === "loading" || status === "unauthenticated" || statsLoading || vendorsLoading) {
        return (
            <div className="space-y-6 animate-pulse">
                <div className="h-8 w-48 rounded-xl bg-gray-200" />
                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="rounded-2xl bg-white border border-gray-100 p-6 h-32" />
                    ))}
                </div>
                <div className="grid gap-5 lg:grid-cols-7">
                    <div className="col-span-4 rounded-2xl bg-white border border-gray-100 h-96" />
                    <div className="col-span-3 rounded-2xl bg-white border border-gray-100 h-96" />
                </div>
            </div>
        );
    }

    if (statsError) {
        return (
            <div className="flex items-center gap-3 rounded-2xl bg-red-50 border border-red-100 p-5 text-red-600">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <p className="text-sm font-medium">Failed to load dashboard. Is the backend running?</p>
            </div>
        );
    }

    const statCards = [
        {
            name: "Total Bookings",
            value: (stats?.totalBookings || 0).toLocaleString(),
            prefix: "PKR",
            icon: TrendingUp,
            color: "bg-violet-50 text-violet-600",
            trend: "+12%",
            trendUp: true,
        },
        {
            name: "Active Vendors",
            value: stats?.activeVendors || 0,
            icon: Store,
            color: "bg-emerald-50 text-emerald-600",
            trend: "+5%",
            trendUp: true,
        },
        {
            name: "Total Users",
            value: stats?.totalUsers || 0,
            icon: Users,
            color: "bg-blue-50 text-blue-600",
            trend: "+18%",
            trendUp: true,
        },
        {
            name: "Pending Approval",
            value: stats?.pendingVendors || 0,
            icon: Clock,
            color: "bg-amber-50 text-amber-600",
            trend: "Awaiting review",
            trendUp: null,
        },
    ];

    return (
        <div className="space-y-6">
            {/* Page header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
                    <p className="mt-1 text-sm text-gray-500">Welcome back — here's what's happening.</p>
                </div>
                <div className="flex items-center gap-2 rounded-xl bg-white border border-gray-100 px-4 py-2 shadow-sm">
                    <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-xs font-medium text-gray-600">Live</span>
                </div>
            </div>

            {/* Stat cards */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {statCards.map((stat) => (
                    <div
                        key={stat.name}
                        className="rounded-2xl bg-white border border-gray-100 p-6 shadow-sm hover:shadow-md transition-shadow duration-200"
                    >
                        <div className="flex items-center justify-between mb-4">
                            <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${stat.color}`}>
                                <stat.icon className="h-5 w-5" />
                            </div>
                            {stat.trendUp !== null ? (
                                <span className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full ${stat.trendUp ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"}`}>
                                    <ArrowUpRight className="h-3 w-3" />
                                    {stat.trend}
                                </span>
                            ) : (
                                <span className="text-xs font-medium text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
                                    {stat.trend}
                                </span>
                            )}
                        </div>
                        <p className="text-2xl font-bold text-gray-900">
                            {stat.prefix && <span className="text-sm font-medium text-gray-400 mr-1">{stat.prefix}</span>}
                            {stat.value}
                        </p>
                        <p className="mt-1 text-sm text-gray-500">{stat.name}</p>
                    </div>
                ))}
            </div>

            {/* Content grid */}
            <div className="grid gap-5 lg:grid-cols-7">
                {/* Overview placeholder */}
                <div className="col-span-4 rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                        <div>
                            <h3 className="font-semibold text-gray-900">Overview</h3>
                            <p className="text-xs text-gray-400 mt-0.5">Platform activity summary</p>
                        </div>
                        <Activity className="h-4 w-4 text-gray-400" />
                    </div>
                    <div className="p-6">
                        <div className="h-72 w-full flex flex-col items-center justify-center rounded-xl bg-gradient-to-br from-gray-50 to-gray-100 border border-dashed border-gray-200">
                            <TrendingUp className="h-10 w-10 text-gray-300 mb-3" />
                            <p className="text-sm font-medium text-gray-400">Analytics charts coming soon</p>
                            <p className="text-xs text-gray-300 mt-1">Real-time data visualization</p>
                        </div>
                    </div>
                </div>

                {/* Recent vendors */}
                <div className="col-span-3 rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                        <div>
                            <h3 className="font-semibold text-gray-900">Recent Vendors</h3>
                            <p className="text-xs text-gray-400 mt-0.5">Newly registered vendors</p>
                        </div>
                        <Store className="h-4 w-4 text-gray-400" />
                    </div>
                    <div className="divide-y divide-gray-50">
                        {recentVendors?.slice(0, 5).map((vendor: any) => {
                            const isPending = vendor.status === "PENDING" || vendor.status === "INACTIVE";
                            const isProcessing = actionVendorId === vendor.id && statusMutation.isPending;

                            return (
                                <div key={vendor.id} className="flex items-center gap-3 px-6 py-3.5 hover:bg-gray-50/50 transition-colors">
                                    <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-100 to-indigo-100 text-violet-600 text-xs font-bold">
                                        {vendor.name.substring(0, 2).toUpperCase()}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-gray-900 truncate">{vendor.name}</p>
                                        <p className="text-xs text-gray-400 capitalize">{vendor.category}</p>
                                    </div>
                                    <div className="flex items-center gap-1.5 flex-shrink-0">
                                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                                            vendor.status === "ACTIVE" ? "bg-emerald-50 text-emerald-700"
                                            : vendor.status === "PENDING" ? "bg-amber-50 text-amber-700"
                                            : vendor.status === "REJECTED" ? "bg-red-50 text-red-700"
                                            : "bg-gray-100 text-gray-500"
                                        }`}>
                                            {vendor.status}
                                        </span>
                                        {isPending && (
                                            <div className="flex gap-1">
                                                <button
                                                    onClick={() => {
                                                        setActionVendorId(vendor.id);
                                                        statusMutation.mutate({ id: vendor.id, newStatus: "ACTIVE" });
                                                    }}
                                                    disabled={isProcessing}
                                                    title="Approve"
                                                    className="flex h-7 w-7 items-center justify-center rounded-lg text-emerald-600 hover:bg-emerald-50 disabled:opacity-40 transition-colors"
                                                >
                                                    {isProcessing ? (
                                                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                    ) : (
                                                        <CheckCircle className="h-3.5 w-3.5" />
                                                    )}
                                                </button>
                                                <button
                                                    onClick={() => {
                                                        setActionVendorId(vendor.id);
                                                        statusMutation.mutate({ id: vendor.id, newStatus: "REJECTED" });
                                                    }}
                                                    disabled={isProcessing}
                                                    title="Reject"
                                                    className="flex h-7 w-7 items-center justify-center rounded-lg text-red-500 hover:bg-red-50 disabled:opacity-40 transition-colors"
                                                >
                                                    <XCircle className="h-3.5 w-3.5" />
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                        {(!recentVendors || recentVendors.length === 0) && (
                            <div className="px-6 py-10 text-center">
                                <Store className="h-8 w-8 text-gray-200 mx-auto mb-2" />
                                <p className="text-sm text-gray-400">No vendors yet</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
