'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { User, Mail, Phone, Lock, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

interface UserData {
    firstName: string;
    lastName: string;
    email: string;
    phone: string;
}

export default function ProfilePage() {
    const router = useRouter();
    const [user, setUser] = useState<UserData>({ firstName: '', lastName: '', email: '', phone: '' });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [editing, setEditing] = useState(false);
    const [passwordForm, setPasswordForm] = useState({ currentPassword: '', newPassword: '', confirmPassword: '' });
    const [changingPassword, setChangingPassword] = useState(false);
    const [showPasswordSection, setShowPasswordSection] = useState(false);

    useEffect(() => {
        const token = localStorage.getItem('userToken');
        if (!token) {
            router.push('/login');
            return;
        }

        // Load user data from localStorage first, then try API
        try {
            const stored = localStorage.getItem('userData');
            if (stored) {
                const parsed = JSON.parse(stored);
                setUser({
                    firstName: parsed.firstName || '',
                    lastName: parsed.lastName || '',
                    email: parsed.email || '',
                    phone: parsed.phone || '',
                });
            }
        } catch { }

        // Try to fetch fresh data from API
        api.get('/users/me')
            .then((res) => {
                const data = res.data?.user || res.data?.data || res.data;
                if (data) {
                    setUser({
                        firstName: data.firstName || '',
                        lastName: data.lastName || '',
                        email: data.email || '',
                        phone: data.phone || '',
                    });
                    localStorage.setItem('userData', JSON.stringify(data));
                }
            })
            .catch(() => {
                // Use localStorage data as fallback
            })
            .finally(() => setLoading(false));
    }, [router]);

    const handleSave = async () => {
        if (!user.firstName.trim()) {
            toast.error('First name is required');
            return;
        }

        setSaving(true);
        try {
            await api.put('/users/me', {
                firstName: user.firstName,
                lastName: user.lastName,
                phone: user.phone,
            });
            localStorage.setItem('userData', JSON.stringify(user));
            toast.success('Profile updated!');
            setEditing(false);
        } catch (err: any) {
            toast.error(err.response?.data?.message || 'Failed to update profile');
        } finally {
            setSaving(false);
        }
    };

    const handlePasswordChange = async () => {
        if (!passwordForm.currentPassword || !passwordForm.newPassword) {
            toast.error('Please fill in all password fields');
            return;
        }
        if (passwordForm.newPassword.length < 8) {
            toast.error('New password must be at least 8 characters');
            return;
        }
        if (passwordForm.newPassword !== passwordForm.confirmPassword) {
            toast.error('New passwords do not match');
            return;
        }

        setChangingPassword(true);
        try {
            await api.put('/users/me/password', {
                currentPassword: passwordForm.currentPassword,
                newPassword: passwordForm.newPassword,
            });
            toast.success('Password changed successfully!');
            setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
            setShowPasswordSection(false);
        } catch (err: any) {
            toast.error(err.response?.data?.message || 'Failed to change password');
        } finally {
            setChangingPassword(false);
        }
    };

    if (loading) {
        return (
            <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
                <div className="h-8 w-40 animate-pulse rounded bg-gray-200" />
                <div className="bg-white rounded-xl shadow-sm p-8 space-y-4">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="space-y-2">
                            <div className="h-3 w-20 animate-pulse rounded bg-gray-200" />
                            <div className="h-10 w-full animate-pulse rounded-lg bg-gray-200" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-2xl mx-auto px-4 py-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-6">My Profile</h1>

            {/* Personal Info */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 mb-6">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <User className="h-5 w-5 text-indigo-600" />
                        Personal Information
                    </h2>
                    {!editing ? (
                        <button
                            onClick={() => setEditing(true)}
                            className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                        >
                            Edit
                        </button>
                    ) : (
                        <div className="flex gap-2">
                            <button
                                onClick={() => setEditing(false)}
                                className="text-sm text-gray-500 hover:text-gray-700"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={saving}
                                className="text-sm bg-indigo-600 text-white px-3 py-1 rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1"
                            >
                                {saving && <Loader2 className="h-3 w-3 animate-spin" />}
                                Save
                            </button>
                        </div>
                    )}
                </div>

                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                            <input
                                type="text"
                                value={user.firstName}
                                onChange={(e) => setUser({ ...user, firstName: e.target.value })}
                                disabled={!editing}
                                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm disabled:bg-gray-50 disabled:text-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                            <input
                                type="text"
                                value={user.lastName}
                                onChange={(e) => setUser({ ...user, lastName: e.target.value })}
                                disabled={!editing}
                                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm disabled:bg-gray-50 disabled:text-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                            />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            <Mail className="inline h-4 w-4 mr-1" /> Email
                        </label>
                        <input
                            type="email"
                            value={user.email}
                            disabled
                            className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm bg-gray-50 text-gray-500"
                        />
                        <p className="text-xs text-gray-400 mt-1">Email cannot be changed</p>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            <Phone className="inline h-4 w-4 mr-1" /> Phone
                        </label>
                        <input
                            type="tel"
                            value={user.phone}
                            onChange={(e) => setUser({ ...user, phone: e.target.value })}
                            disabled={!editing}
                            placeholder="+92 300 1234567"
                            className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm disabled:bg-gray-50 disabled:text-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        />
                    </div>
                </div>
            </div>

            {/* Change Password */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
                <button
                    onClick={() => setShowPasswordSection(!showPasswordSection)}
                    className="flex items-center justify-between w-full"
                >
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <Lock className="h-5 w-5 text-indigo-600" />
                        Change Password
                    </h2>
                    <span className="text-sm text-indigo-600">{showPasswordSection ? 'Hide' : 'Show'}</span>
                </button>

                {showPasswordSection && (
                    <div className="mt-6 space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
                            <input
                                type="password"
                                value={passwordForm.currentPassword}
                                onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                            <input
                                type="password"
                                value={passwordForm.newPassword}
                                onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                                placeholder="Min 8 characters"
                                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
                            <input
                                type="password"
                                value={passwordForm.confirmPassword}
                                onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                            />
                        </div>
                        <button
                            onClick={handlePasswordChange}
                            disabled={changingPassword}
                            className="w-full bg-indigo-600 text-white py-2.5 px-4 rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                            {changingPassword ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Changing...
                                </>
                            ) : (
                                'Update Password'
                            )}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
