'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, Save } from 'lucide-react';
import Link from 'next/link';
import { useAuthStore } from '@/lib/auth-store';
import { api, getApiError } from '@/lib/api';
import { cn } from '@/lib/utils';

const categories = [
    'venue', 'catering', 'photography', 'videography',
    'music', 'decoration', 'transportation', 'accommodation',
    'planning', 'entertainment', 'equipment', 'staffing', 'other',
] as const;

const unitTypes = [
    { value: 'per_hour', label: 'Per Hour' },
    { value: 'per_day', label: 'Per Day' },
    { value: 'per_event', label: 'Per Event' },
    { value: 'per_person', label: 'Per Person' },
    { value: 'per_unit', label: 'Per Unit' },
    { value: 'flat_rate', label: 'Flat Rate' },
];

export default function NewServicePage() {
    const router = useRouter();
    const { isAuthenticated } = useAuthStore();
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasMounted, setHasMounted] = useState(false);

    const [form, setForm] = useState({
        name: '',
        category: 'catering' as typeof categories[number],
        description: '',
        shortDescription: '',
        unitType: 'per_event',
        capacity: '',
        minQuantity: '1',
        maxQuantity: '',
        leadTimeDays: '0',
        isActive: true,
    });

    useEffect(() => { setHasMounted(true); }, []);

    useEffect(() => {
        if (hasMounted && !isAuthenticated) {
            router.push('/login');
        }
    }, [hasMounted, isAuthenticated, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setError(null);

        try {
            const payload: any = {
                name: form.name,
                category: form.category,
                description: form.description || undefined,
                shortDescription: form.shortDescription || undefined,
                unitType: form.unitType,
                minQuantity: parseInt(form.minQuantity) || 1,
                isActive: form.isActive,
                leadTimeDays: parseInt(form.leadTimeDays) || 0,
            };
            if (form.capacity) payload.capacity = parseInt(form.capacity);
            if (form.maxQuantity) payload.maxQuantity = parseInt(form.maxQuantity);

            await api.post('/vendors/me/services', payload);
            router.push('/services');
        } catch (err: any) {
            setError(getApiError(err));
        } finally {
            setSaving(false);
        }
    };

    if (!hasMounted || !isAuthenticated) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link
                    href="/services"
                    className="rounded-lg p-2 text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-800"
                >
                    <ArrowLeft className="h-5 w-5" />
                </Link>
                <div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Add New Service</h1>
                    <p className="mt-1 text-surface-500 dark:text-surface-400">Create a new service offering</p>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
                    {error}
                </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
                <div className="rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-900">
                    <h2 className="mb-4 text-lg font-semibold text-surface-900 dark:text-surface-50">Basic Information</h2>
                    <div className="grid gap-4 sm:grid-cols-2">
                        <div className="sm:col-span-2">
                            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                Service Name *
                            </label>
                            <input
                                type="text"
                                required
                                value={form.name}
                                onChange={(e) => setForm({ ...form, name: e.target.value })}
                                placeholder="e.g. Premium Wedding Photography"
                                className="w-full rounded-lg border border-surface-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                            />
                        </div>
                        <div>
                            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                Category *
                            </label>
                            <select
                                value={form.category}
                                onChange={(e) => setForm({ ...form, category: e.target.value as typeof categories[number] })}
                                className="w-full rounded-lg border border-surface-300 px-4 py-2.5 text-sm capitalize focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                            >
                                {categories.map((cat) => (
                                    <option key={cat} value={cat} className="capitalize">{cat}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                Unit Type
                            </label>
                            <select
                                value={form.unitType}
                                onChange={(e) => setForm({ ...form, unitType: e.target.value })}
                                className="w-full rounded-lg border border-surface-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                            >
                                {unitTypes.map((u) => (
                                    <option key={u.value} value={u.value}>{u.label}</option>
                                ))}
                            </select>
                        </div>
                        <div className="sm:col-span-2">
                            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                Short Description
                            </label>
                            <input
                                type="text"
                                value={form.shortDescription}
                                onChange={(e) => setForm({ ...form, shortDescription: e.target.value })}
                                placeholder="Brief summary (max 500 chars)"
                                maxLength={500}
                                className="w-full rounded-lg border border-surface-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                            />
                        </div>
                        <div className="sm:col-span-2">
                            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                Full Description
                            </label>
                            <textarea
                                value={form.description}
                                onChange={(e) => setForm({ ...form, description: e.target.value })}
                                placeholder="Detailed description of your service..."
                                rows={4}
                                maxLength={5000}
                                className="w-full rounded-lg border border-surface-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                            />
                        </div>
                    </div>
                </div>

                <div className="rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-900">
                    <h2 className="mb-4 text-lg font-semibold text-surface-900 dark:text-surface-50">Capacity & Booking</h2>
                    <div className="grid gap-4 sm:grid-cols-3">
                        <div>
                            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                Capacity (guests)
                            </label>
                            <input
                                type="number"
                                value={form.capacity}
                                onChange={(e) => setForm({ ...form, capacity: e.target.value })}
                                placeholder="e.g. 200"
                                min="1"
                                className="w-full rounded-lg border border-surface-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                            />
                        </div>
                        <div>
                            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                Min Quantity
                            </label>
                            <input
                                type="number"
                                value={form.minQuantity}
                                onChange={(e) => setForm({ ...form, minQuantity: e.target.value })}
                                min="1"
                                className="w-full rounded-lg border border-surface-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                            />
                        </div>
                        <div>
                            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                Lead Time (days)
                            </label>
                            <input
                                type="number"
                                value={form.leadTimeDays}
                                onChange={(e) => setForm({ ...form, leadTimeDays: e.target.value })}
                                min="0"
                                className="w-full rounded-lg border border-surface-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                            />
                        </div>
                    </div>
                </div>

                <div className="rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-900">
                    <div className="flex items-center gap-3">
                        <input
                            type="checkbox"
                            id="isActive"
                            checked={form.isActive}
                            onChange={(e) => setForm({ ...form, isActive: e.target.checked })}
                            className="h-4 w-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                        />
                        <label htmlFor="isActive" className="text-sm font-medium text-surface-700 dark:text-surface-300">
                            Service is active and visible to clients
                        </label>
                    </div>
                </div>

                {/* Submit */}
                <div className="flex items-center justify-end gap-3">
                    <Link
                        href="/services"
                        className="rounded-lg border border-surface-300 px-4 py-2.5 text-sm font-medium text-surface-700 hover:bg-surface-100 dark:border-surface-700 dark:text-surface-300"
                    >
                        Cancel
                    </Link>
                    <button
                        type="submit"
                        disabled={saving || !form.name}
                        className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                    >
                        {saving ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Save className="h-4 w-4" />
                        )}
                        {saving ? 'Creating...' : 'Create Service'}
                    </button>
                </div>
            </form>
        </div>
    );
}
