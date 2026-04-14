'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { User, Building2, Mail, Phone, Globe, MapPin, Shield, Loader2, Save, CheckCircle } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { api, getApiError } from '@/lib/api';

export default function ProfilePage() {
    const router = useRouter();
    const { isAuthenticated, user, vendor } = useAuthStore();
    const [editing, setEditing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasMounted, setHasMounted] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        contactEmail: '',
        phone: '',
        website: '',
    });

    useEffect(() => { setHasMounted(true); }, []);

    useEffect(() => {
        if (hasMounted && !isAuthenticated) {
            router.push('/login');
        }
    }, [hasMounted, isAuthenticated, router]);

    useEffect(() => {
        if (vendor) {
            setFormData({
                name: vendor.name || '',
                description: vendor.description || '',
                contactEmail: vendor.contactEmail || '',
                phone: vendor.phone || '',
                website: vendor.website || '',
            });
        }
    }, [vendor]);

    if (!hasMounted || !isAuthenticated) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
            </div>
        );
    }

    const handleSave = async () => {
        // Validate required fields
        if (!formData.name?.trim()) {
            setError('Business name is required');
            return;
        }
        if (formData.contactEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.contactEmail)) {
            setError('Please enter a valid email address');
            return;
        }
        if (formData.website && formData.website.trim() && !/^https?:\/\/.+/.test(formData.website)) {
            setError('Website must start with http:// or https://');
            return;
        }

        setSaving(true);
        setError(null);
        setSuccess(false);
        try {
            await api.put('/vendors/me', formData);
            setSuccess(true);
            setEditing(false);
            setTimeout(() => setSuccess(false), 3000);
        } catch (err: any) {
            setError(getApiError(err));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-6 max-w-3xl">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-surface-900">Profile</h1>
                    <p className="text-surface-500 mt-1">Manage your vendor profile and business information</p>
                </div>
                {!editing ? (
                    <button
                        onClick={() => setEditing(true)}
                        className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                    >
                        Edit Profile
                    </button>
                ) : (
                    <div className="flex gap-2">
                        <button
                            onClick={() => setEditing(false)}
                            className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg hover:bg-surface-200 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2 disabled:opacity-50"
                        >
                            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                            Save Changes
                        </button>
                    </div>
                )}
            </div>

            {success && (
                <div className="flex items-center gap-2 p-4 bg-green-50 text-green-700 rounded-xl border border-green-200">
                    <CheckCircle className="h-5 w-5" />
                    Profile updated successfully
                </div>
            )}
            {error && (
                <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200">{error}</div>
            )}

            {/* User Info */}
            <div className="bg-white rounded-xl shadow-sm border border-surface-100 p-6">
                <div className="flex items-center gap-4 mb-6">
                    <div className="h-16 w-16 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center text-xl font-bold">
                        {user?.firstName?.[0]}{user?.lastName?.[0]}
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-surface-900">{user?.firstName} {user?.lastName}</h2>
                        <p className="text-surface-500">{user?.email}</p>
                        <div className="flex items-center gap-2 mt-1">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${vendor?.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                                {vendor?.status}
                            </span>
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
                                {vendor?.tier} Tier
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Business Info */}
            <div className="bg-white rounded-xl shadow-sm border border-surface-100 p-6 space-y-5">
                <h3 className="text-lg font-semibold text-surface-900 flex items-center gap-2">
                    <Building2 className="h-5 w-5 text-primary-600" />
                    Business Information
                </h3>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-surface-700 mb-1">Business Name</label>
                        {editing ? (
                            <input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full rounded-lg border border-surface-300 px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
                        ) : (
                            <p className="text-surface-900 py-2">{vendor?.name}</p>
                        )}
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-surface-700 mb-1">Description</label>
                        {editing ? (
                            <textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} rows={3} className="w-full rounded-lg border border-surface-300 px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
                        ) : (
                            <p className="text-surface-900 py-2">{vendor?.description || 'No description'}</p>
                        )}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Contact Email</label>
                            {editing ? (
                                <input value={formData.contactEmail} onChange={(e) => setFormData({ ...formData, contactEmail: e.target.value })} className="w-full rounded-lg border border-gray-300 px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
                            ) : (
                                <p className="text-gray-900 py-2 flex items-center gap-2"><Mail className="h-4 w-4 text-gray-400" />{vendor?.contactEmail}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                            {editing ? (
                                <input value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} className="w-full rounded-lg border border-gray-300 px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
                            ) : (
                                <p className="text-gray-900 py-2 flex items-center gap-2"><Phone className="h-4 w-4 text-gray-400" />{vendor?.phone || 'Not set'}</p>
                            )}
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Website</label>
                        {editing ? (
                            <input value={formData.website} onChange={(e) => setFormData({ ...formData, website: e.target.value })} className="w-full rounded-lg border border-gray-300 px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
                        ) : (
                            <p className="text-gray-900 py-2 flex items-center gap-2"><Globe className="h-4 w-4 text-gray-400" />{vendor?.website || 'Not set'}</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Security */}
            <div className="bg-white rounded-xl shadow-sm border border-surface-100 p-6">
                <h3 className="text-lg font-semibold text-surface-900 flex items-center gap-2 mb-4">
                    <Shield className="h-5 w-5 text-primary-600" />
                    Security
                </h3>
                <div className="space-y-3">
                    <div className="flex items-center justify-between py-3 border-b border-surface-100">
                        <div>
                            <p className="font-medium text-surface-900">Two-Factor Authentication</p>
                            <p className="text-sm text-surface-500">Add an extra layer of security</p>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${user?.twoFactorEnabled ? 'bg-green-100 text-green-800' : 'bg-surface-100 text-surface-600'}`}>
                            {user?.twoFactorEnabled ? 'Enabled' : 'Disabled'}
                        </span>
                    </div>
                    <div className="flex items-center justify-between py-3">
                        <div>
                            <p className="font-medium text-surface-900">Email Verification</p>
                            <p className="text-sm text-surface-500">Verify your email address</p>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${user?.emailVerified ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                            {user?.emailVerified ? 'Verified' : 'Unverified'}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
