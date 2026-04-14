'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
    Plus,
    Search,
    Edit,
    Trash2,
    Eye,
    Package,
    Loader2,
    AlertCircle,
    RefreshCw,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { cn } from '@/lib/utils';
import { api, getApiError } from '@/lib/api';

interface Service {
    id: string;
    name: string;
    category: string;
    description: string | null;
    isActive: boolean;
    capacity: number | null;
    duration: string | null;
    createdAt: string;
    pricings?: any[];
}

interface ServicesResponse {
    data: Service[];
    total: number;
    page: number;
    limit: number;
}

const categories = ['All', 'catering', 'photography', 'videography', 'entertainment', 'decoration', 'venue', 'music', 'transportation', 'planning'];

export default function ServicesPage() {
    const router = useRouter();
    const { isAuthenticated } = useAuthStore();
    const [services, setServices] = useState<Service[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('All');
    const [deleting, setDeleting] = useState<string | null>(null);
    const [hasMounted, setHasMounted] = useState(false);

    // Prevent hydration mismatch
    useEffect(() => {
        setHasMounted(true);
    }, []);

    // Redirect if not authenticated
    useEffect(() => {
        if (!hasMounted) return;
        if (!isAuthenticated) {
            router.push('/login');
        }
    }, [hasMounted, isAuthenticated, router]);

    // Fetch services from backend API
    const fetchServices = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params: any = {};
            if (searchQuery) params.search = searchQuery;
            if (categoryFilter !== 'All') params.category = categoryFilter;

            const response = await api.get('/vendors/me/services', { params });
            const data = response.data;

            // Handle both { data: [...] } and direct array responses
            setServices(Array.isArray(data) ? data : (data.data || []));
        } catch (err: any) {
            const msg = getApiError(err);
            setError(msg);
            console.error('Failed to fetch services:', msg);
        } finally {
            setLoading(false);
        }
    }, [searchQuery, categoryFilter]);

    useEffect(() => {
        if (hasMounted && isAuthenticated) {
            fetchServices();
        }
    }, [hasMounted, isAuthenticated, fetchServices]);

    // Delete service
    const handleDelete = async (serviceId: string) => {
        if (!confirm('Are you sure you want to delete this service?')) return;

        setDeleting(serviceId);
        try {
            await api.delete(`/vendors/me/services/${serviceId}`);
            setServices((prev) => prev.filter((s) => s.id !== serviceId));
        } catch (err: any) {
            alert(`Failed to delete: ${getApiError(err)}`);
        } finally {
            setDeleting(null);
        }
    };

    const getStatusColor = (isActive: boolean) =>
        isActive
            ? 'bg-green-100 text-green-700 border-green-200'
            : 'bg-gray-100 text-gray-700 border-gray-200';

    const activeServices = services.filter((s) => s.isActive);
    const uniqueCategories = new Set(services.map((s) => s.category));

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Services</h1>
                    <p className="mt-1 text-surface-500 dark:text-surface-400">
                        Manage your service offerings
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={fetchServices}
                        aria-label="Refresh services list"
                        className="inline-flex items-center gap-2 rounded-lg border border-surface-300 px-3 py-2 text-sm text-surface-700 transition-colors hover:bg-surface-100 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-800"
                    >
                        <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
                        Refresh
                    </button>
                    <Link
                        href="/services/new"
                        className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-white transition-colors hover:bg-primary-700"
                    >
                        <Plus className="h-4 w-4" />
                        Add Service
                    </Link>
                </div>
            </div>

            {/* Stats */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                    { label: 'Total Services', value: services.length },
                    { label: 'Active Services', value: activeServices.length },
                    { label: 'Categories', value: uniqueCategories.size },
                    { label: 'Inactive', value: services.length - activeServices.length },
                ].map((stat, index) => (
                    <div
                        key={index}
                        className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-900"
                    >
                        <div className="flex items-center gap-3">
                            <div className="rounded-lg bg-primary-100 p-2 dark:bg-primary-900/30">
                                <Package className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                            </div>
                            <div>
                                <p className="text-sm text-surface-500 dark:text-surface-400">{stat.label}</p>
                                <p className="text-lg font-semibold text-surface-900 dark:text-surface-50">{stat.value}</p>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Filters */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap gap-2">
                    {categories.map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setCategoryFilter(cat)}
                            className={cn(
                                'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors capitalize',
                                cat === categoryFilter
                                    ? 'bg-primary-600 text-white'
                                    : 'bg-surface-100 text-surface-700 hover:bg-surface-200 dark:bg-surface-800 dark:text-surface-300'
                            )}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" aria-hidden="true" />
                    <input
                        type="text"
                        placeholder="Search services..."
                        aria-label="Search services"
                        className="w-full rounded-lg border border-surface-300 pl-10 pr-4 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
                    <AlertCircle className="h-5 w-5 text-red-500" />
                    <div className="flex-1">
                        <p className="text-sm font-medium text-red-800 dark:text-red-200">Failed to load services</p>
                        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                    </div>
                    <button
                        onClick={fetchServices}
                        className="rounded-lg bg-red-100 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-300"
                    >
                        Retry
                    </button>
                </div>
            )}

            {/* Loading Skeleton */}
            {loading && (
                <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="border-b border-surface-200 bg-surface-50 dark:border-surface-800 dark:bg-surface-900/50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 dark:text-surface-300">Service</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 dark:text-surface-300">Category</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 dark:text-surface-300">Status</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 dark:text-surface-300">Capacity</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 dark:text-surface-300">Pricing</th>
                                    <th className="px-4 py-3 text-right text-sm font-medium text-surface-700 dark:text-surface-300">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {[...Array(5)].map((_, i) => (
                                    <tr key={i} className="border-b border-surface-100 dark:border-surface-800">
                                        <td className="px-4 py-4"><div className="h-4 w-32 animate-pulse rounded bg-surface-200 dark:bg-surface-700" /></td>
                                        <td className="px-4 py-4"><div className="h-4 w-20 animate-pulse rounded bg-surface-200 dark:bg-surface-700" /></td>
                                        <td className="px-4 py-4"><div className="h-6 w-16 animate-pulse rounded-full bg-surface-200 dark:bg-surface-700" /></td>
                                        <td className="px-4 py-4"><div className="h-4 w-12 animate-pulse rounded bg-surface-200 dark:bg-surface-700" /></td>
                                        <td className="px-4 py-4"><div className="h-4 w-24 animate-pulse rounded bg-surface-200 dark:bg-surface-700" /></td>
                                        <td className="px-4 py-4 text-right"><div className="ml-auto h-4 w-16 animate-pulse rounded bg-surface-200 dark:bg-surface-700" /></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Services Table */}
            {!loading && !error && (
                <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="border-b border-surface-200 bg-surface-50 dark:border-surface-800 dark:bg-surface-900/50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 dark:text-surface-300">Service</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 dark:text-surface-300">Category</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 dark:text-surface-300">Status</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 dark:text-surface-300">Capacity</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 dark:text-surface-300">Pricing</th>
                                    <th className="px-4 py-3 text-right text-sm font-medium text-surface-700 dark:text-surface-300">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-surface-200 dark:divide-surface-800">
                                {services.map((service) => (
                                    <tr key={service.id} className="hover:bg-surface-50 dark:hover:bg-surface-900/50">
                                        <td className="px-4 py-4">
                                            <div>
                                                <p className="font-medium text-surface-900 dark:text-surface-50">{service.name}</p>
                                                <p className="text-sm text-surface-500 dark:text-surface-400 line-clamp-1">{service.description || 'No description'}</p>
                                            </div>
                                        </td>
                                        <td className="px-4 py-4">
                                            <span className="rounded-full bg-surface-100 px-2 py-1 text-xs font-medium capitalize text-surface-700 dark:bg-surface-800 dark:text-surface-300">
                                                {service.category}
                                            </span>
                                        </td>
                                        <td className="px-4 py-4">
                                            <span className={cn(
                                                'inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs font-medium',
                                                getStatusColor(service.isActive)
                                            )}>
                                                <span className={cn(
                                                    'h-1.5 w-1.5 rounded-full',
                                                    service.isActive ? 'bg-green-600' : 'bg-gray-600'
                                                )} />
                                                {service.isActive ? 'Active' : 'Inactive'}
                                            </span>
                                        </td>
                                        <td className="px-4 py-4 text-sm text-surface-600 dark:text-surface-400">
                                            {service.capacity ? `${service.capacity} guests` : service.duration || 'N/A'}
                                        </td>
                                        <td className="px-4 py-4 text-sm text-surface-600 dark:text-surface-400">
                                            {service.pricings?.length || 0} packages
                                        </td>
                                        <td className="px-4 py-4">
                                            <div className="flex items-center justify-end gap-2">
                                                <Link
                                                    href={`/services/${service.id}`}
                                                    className="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800"
                                                    title="View"
                                                >
                                                    <Eye className="h-4 w-4" />
                                                </Link>
                                                <Link
                                                    href={`/services/${service.id}/edit`}
                                                    className="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800"
                                                    title="Edit"
                                                >
                                                    <Edit className="h-4 w-4" />
                                                </Link>
                                                <button
                                                    onClick={() => handleDelete(service.id)}
                                                    disabled={deleting === service.id}
                                                    className="rounded-lg p-1.5 text-surface-500 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 disabled:opacity-50"
                                                    title="Delete"
                                                >
                                                    {deleting === service.id ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <Trash2 className="h-4 w-4" />
                                                    )}
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {services.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-12">
                            <Package className="h-12 w-12 text-surface-300 dark:text-surface-700" />
                            <p className="mt-4 text-surface-500 dark:text-surface-400">No services found</p>
                            <Link
                                href="/services/new"
                                className="mt-4 inline-flex items-center gap-2 text-primary-600 hover:underline"
                            >
                                <Plus className="h-4 w-4" />
                                Add your first service
                            </Link>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
