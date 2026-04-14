'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
    LayoutDashboard,
    Briefcase,
    DollarSign,
    Calendar,
    Key,
    Settings,
    LogOut,
    ChevronRight,
    TrendingUp,
    Users,
    Package,
    Bell,
    Menu,
    Loader2,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { cn, formatCurrency, tierColors, getInitials } from '@/lib/utils';
import { api } from '@/lib/api';

const navItems = [
    { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/services', icon: Briefcase, label: 'Services' },
    { href: '/pricing', icon: DollarSign, label: 'Pricing' },
    { href: '/availability', icon: Calendar, label: 'Availability' },
    { href: '/bookings', icon: Package, label: 'Bookings' },
    { href: '/api-integration', icon: Key, label: 'API Integration' },
    { href: '/profile', icon: Settings, label: 'Profile' },
];

interface DashboardStats {
    totalServices: number;
    activeServices: number;
    totalBookings: number;
    pendingBookings: number;
}

interface RecentBooking {
    id: string;
    eventDate: string;
    status: string;
    totalAmount: number | null;
    vendor?: { name: string };
    service?: { name: string };
}


export default function DashboardPage() {
    const router = useRouter();
    const { user, vendor, isAuthenticated, logout, fetchProfile } = useAuthStore();
    const [dashStats, setDashStats] = useState<DashboardStats>({ totalServices: 0, activeServices: 0, totalBookings: 0, pendingBookings: 0 });
    const [recentBookings, setRecentBookings] = useState<RecentBooking[]>([]);
    const [loadingDash, setLoadingDash] = useState(true);
    const [hasMounted, setHasMounted] = useState(false);

    // Prevent hydration mismatch — wait for client mount before reading auth state
    useEffect(() => {
        setHasMounted(true);
    }, []);

    useEffect(() => {
        if (!hasMounted) return;
        if (!isAuthenticated) {
            router.push('/login');
            return;
        }
        fetchProfile();

        // Fetch dashboard stats from API
        const fetchDashboard = async () => {
            try {
                const response = await api.get('/vendors/me/dashboard');
                setDashStats(response.data.stats || { totalServices: 0, activeServices: 0, totalBookings: 0, pendingBookings: 0 });
                setRecentBookings(response.data.recentActivity || []);
            } catch (err) {
                console.error('Failed to fetch dashboard:', err);
            } finally {
                setLoadingDash(false);
            }
        };
        fetchDashboard();
    }, [hasMounted, isAuthenticated, router, fetchProfile]);

    const handleLogout = async () => {
        await logout();
        router.push('/login');
    };

    const stats = [
        { label: 'Total Bookings', value: String(dashStats.totalBookings), icon: Calendar },
        { label: 'Pending', value: String(dashStats.pendingBookings), icon: TrendingUp },
        { label: 'Active Services', value: String(dashStats.activeServices), icon: Package },
        { label: 'Total Services', value: String(dashStats.totalServices), icon: Users },
    ];

    // Show loading spinner until mounted + auth checked
    if (!hasMounted || !isAuthenticated || !vendor) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
            </div>
        );
    }

    // Skeleton component for shimmer loading
    const Skeleton = ({ className = '' }: { className?: string }) => (
        <div className={`animate-pulse bg-surface-200 rounded-lg ${className}`} />
    );

    return (
        <div className="flex min-h-screen bg-surface-50 dark:bg-surface-950">
            {/* Sidebar */}
            <aside className="fixed inset-y-0 left-0 z-50 w-64 border-r border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
                {/* Logo */}
                <div className="flex h-16 items-center gap-3 border-b border-surface-200 px-6 dark:border-surface-800">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-600">
                        <Package className="h-5 w-5 text-white" />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-surface-900 dark:text-surface-50">Vendor Portal</p>
                        <p className="text-xs text-surface-500">Event Orchestrator</p>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex flex-col gap-1 p-4">
                    {navItems.map((item) => {
                        const isActive = item.href === '/dashboard';
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                                    isActive
                                        ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                                        : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 dark:hover:text-surface-50'
                                )}
                            >
                                <item.icon className="h-5 w-5" />
                                {item.label}
                            </Link>
                        );
                    })}
                </nav>

                {/* User Section */}
                <div className="absolute bottom-0 left-0 right-0 border-t border-surface-200 p-4 dark:border-surface-800">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 text-sm font-medium text-primary-700 dark:bg-primary-900/30 dark:text-primary-400">
                            {getInitials(user?.firstName ? `${user.firstName} ${user.lastName}` : vendor.name)}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="truncate text-sm font-medium text-surface-900 dark:text-surface-50">
                                {user?.firstName} {user?.lastName}
                            </p>
                            <p className="truncate text-xs text-surface-500">{user?.email}</p>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="rounded-lg p-2 text-surface-400 hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800"
                        >
                            <LogOut className="h-5 w-5" />
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="ml-64 flex-1 p-8">
                {/* Header */}
                <div className="mb-8 flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">
                            Welcome back, {user?.firstName}!
                        </h1>
                        <p className="mt-1 text-surface-500 dark:text-surface-400">
                            Here&apos;s what&apos;s happening with your business today.
                        </p>
                    </div>
                    <div className="flex items-center gap-4">
                        <span className={cn('badge', tierColors[vendor.tier])}>
                            {vendor.tier} Vendor
                        </span>
                        <button className="relative rounded-lg p-2 text-surface-400 hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800">
                            <Bell className="h-5 w-5" />
                            <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-error-500" />
                        </button>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="mb-8 grid grid-cols-4 gap-6">
                    {stats.map((stat) => (
                        <div key={stat.label} className="card">
                            <div className="flex items-center justify-between">
                                <div className="rounded-lg bg-primary-50 p-2.5 dark:bg-primary-900/20">
                                    <stat.icon className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                                </div>
                            </div>
                            <div className="mt-4">
                                <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{stat.value}</p>
                                <p className="text-sm text-surface-500 dark:text-surface-400">{stat.label}</p>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Content Grid */}
                <div className="grid grid-cols-3 gap-6">
                    {/* Recent Bookings */}
                    <div className="col-span-2 card">
                        <div className="mb-4 flex items-center justify-between">
                            <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50">
                                Recent Bookings
                            </h2>
                            <Link
                                href="/bookings"
                                className="flex items-center text-sm font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400"
                            >
                                View all
                                <ChevronRight className="ml-1 h-4 w-4" />
                            </Link>
                        </div>
                        <div className="overflow-hidden rounded-lg border border-surface-200 dark:border-surface-700">
                            <table className="w-full">
                                <thead>
                                    <tr className="bg-surface-50 dark:bg-surface-800">
                                        <th className="table-header">Event</th>
                                        <th className="table-header">Date</th>
                                        <th className="table-header">Status</th>
                                        <th className="table-header text-right">Amount</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recentBookings.map((booking) => (
                                        <tr key={booking.id} className="table-row-hover">
                                            <td className="table-cell font-medium">{booking.service?.name || 'N/A'}</td>
                                            <td className="table-cell">{booking.eventDate ? new Date(booking.eventDate).toLocaleDateString() : 'N/A'}</td>
                                            <td className="table-cell">
                                                <span className={cn(
                                                    'badge',
                                                    booking.status === 'confirmed' ? 'badge-success' : 'badge-warning'
                                                )}>
                                                    {booking.status}
                                                </span>
                                            </td>
                                            <td className="table-cell text-right font-medium">
                                                {booking.totalAmount ? formatCurrency(Number(booking.totalAmount)) : 'N/A'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="card">
                        <h2 className="mb-4 text-lg font-semibold text-surface-900 dark:text-surface-50">
                            Quick Actions
                        </h2>
                        <div className="space-y-3">
                            <Link
                                href="/services/new"
                                className="flex items-center gap-3 rounded-lg border border-surface-200 p-3 transition-colors hover:border-primary-200 hover:bg-primary-50/50 dark:border-surface-700 dark:hover:border-primary-800 dark:hover:bg-primary-900/10"
                            >
                                <div className="rounded-lg bg-primary-100 p-2 dark:bg-primary-900/30">
                                    <Package className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                                </div>
                                <div>
                                    <p className="font-medium text-surface-900 dark:text-surface-50">Add Service</p>
                                    <p className="text-xs text-surface-500">Create a new offering</p>
                                </div>
                            </Link>
                            <Link
                                href="/pricing"
                                className="flex items-center gap-3 rounded-lg border border-surface-200 p-3 transition-colors hover:border-primary-200 hover:bg-primary-50/50 dark:border-surface-700 dark:hover:border-primary-800 dark:hover:bg-primary-900/10"
                            >
                                <div className="rounded-lg bg-success-100 p-2 dark:bg-success-900/30">
                                    <DollarSign className="h-5 w-5 text-success-600 dark:text-success-400" />
                                </div>
                                <div>
                                    <p className="font-medium text-surface-900 dark:text-surface-50">Update Pricing</p>
                                    <p className="text-xs text-surface-500">Manage your rates</p>
                                </div>
                            </Link>
                            <Link
                                href="/api-integration"
                                className="flex items-center gap-3 rounded-lg border border-surface-200 p-3 transition-colors hover:border-primary-200 hover:bg-primary-50/50 dark:border-surface-700 dark:hover:border-primary-800 dark:hover:bg-primary-900/10"
                            >
                                <div className="rounded-lg bg-warning-100 p-2 dark:bg-warning-900/30">
                                    <Key className="h-5 w-5 text-warning-600 dark:text-warning-400" />
                                </div>
                                <div>
                                    <p className="font-medium text-surface-900 dark:text-surface-50">API Settings</p>
                                    <p className="text-xs text-surface-500">Configure integrations</p>
                                </div>
                            </Link>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
