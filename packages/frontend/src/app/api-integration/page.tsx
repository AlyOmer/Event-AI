'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Key, Copy, Eye, EyeOff, Plus, Trash2, Loader2, CheckCircle, Shield, Clock } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { api, getApiError } from '@/lib/api';

interface ApiKeyItem {
    id: string;
    name: string;
    keyPrefix: string;
    lastUsedAt: string | null;
    createdAt: string;
    expiresAt: string | null;
    isActive: boolean;
}

export default function ApiIntegrationPage() {
    const router = useRouter();
    const { isAuthenticated, vendor } = useAuthStore();
    const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [creating, setCreating] = useState(false);
    const [newKeyName, setNewKeyName] = useState('');
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [hasMounted, setHasMounted] = useState(false);

    useEffect(() => { setHasMounted(true); }, []);

    useEffect(() => {
        if (hasMounted && !isAuthenticated) {
            router.push('/login');
        }
    }, [hasMounted, isAuthenticated, router]);

    useEffect(() => {
        if (!hasMounted || !isAuthenticated) return;
        fetchKeys();
    }, [hasMounted, isAuthenticated]);

    const fetchKeys = async () => {
        setLoading(true);
        try {
            const response = await api.get('/vendors/me/api-keys');
            setApiKeys(response.data?.data || response.data || []);
        } catch (err: any) {
            setError(getApiError(err));
        } finally {
            setLoading(false);
        }
    };

    const handleCreateKey = async () => {
        if (!newKeyName.trim()) return;
        setCreating(true);
        try {
            await api.post('/vendors/me/api-keys', { name: newKeyName.trim() });
            setNewKeyName('');
            setShowCreateForm(false);
            await fetchKeys();
        } catch (err: any) {
            setError(getApiError(err));
        } finally {
            setCreating(false);
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
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">API Integration</h1>
                    <p className="text-gray-500 mt-1">Manage your API keys and integration settings</p>
                </div>
                <button
                    onClick={() => setShowCreateForm(true)}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2"
                >
                    <Plus className="h-4 w-4" />
                    Create API Key
                </button>
            </div>

            {/* API Status */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${vendor?.apiEnabled ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
                            <Shield className="h-5 w-5" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-gray-900">API Access</h3>
                            <p className="text-sm text-gray-500">
                                {vendor?.apiEnabled ? 'API access is enabled for your account' : 'API access is not yet enabled — contact support'}
                            </p>
                        </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${vendor?.apiEnabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                        {vendor?.apiEnabled ? 'Active' : 'Inactive'}
                    </span>
                </div>
            </div>

            {/* Create Key Form */}
            {showCreateForm && (
                <div className="bg-blue-50 rounded-xl border border-blue-200 p-6">
                    <h3 className="font-semibold text-gray-900 mb-3">Create New API Key</h3>
                    <div className="flex gap-3">
                        <input
                            type="text"
                            value={newKeyName}
                            onChange={(e) => setNewKeyName(e.target.value)}
                            placeholder="Key name (e.g., Production, Staging)"
                            className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        />
                        <button
                            onClick={() => { setShowCreateForm(false); setNewKeyName(''); }}
                            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleCreateKey}
                            disabled={!newKeyName.trim() || creating}
                            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                        >
                            {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4" />}
                            Generate
                        </button>
                    </div>
                </div>
            )}

            {/* API Keys List */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h3 className="font-semibold text-gray-900">API Keys</h3>
                </div>
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
                    </div>
                ) : apiKeys.length === 0 ? (
                    <div className="text-center py-20">
                        <Key className="mx-auto h-12 w-12 text-gray-300 mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-1">No API keys</h3>
                        <p className="text-gray-500">Create an API key to start integrating with the platform</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100">
                        {apiKeys.map((key) => (
                            <div key={key.id} className="px-6 py-4 flex items-center justify-between">
                                <div>
                                    <p className="font-medium text-gray-900">{key.name}</p>
                                    <p className="text-sm text-gray-500 font-mono">{key.keyPrefix}...•••••</p>
                                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                                        <span className="flex items-center gap-1"><Clock className="h-3 w-3" />Created {new Date(key.createdAt).toLocaleDateString()}</span>
                                        {key.lastUsedAt && <span>Last used {new Date(key.lastUsedAt).toLocaleDateString()}</span>}
                                    </div>
                                </div>
                                <span className={`px-2 py-1 rounded text-xs font-medium ${key.isActive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                    {key.isActive ? 'Active' : 'Revoked'}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Documentation Link */}
            <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-xl border border-primary-100 p-6">
                <h3 className="font-semibold text-gray-900 mb-2">API Documentation</h3>
                <p className="text-gray-600 text-sm mb-3">
                    Use your API key to integrate with our platform. Include it in the <code className="bg-white px-1.5 py-0.5 rounded text-primary-600 text-xs">X-API-Key</code> header with each request.
                </p>
                <p className="text-sm text-gray-500">
                    Base URL: <code className="bg-white px-1.5 py-0.5 rounded text-gray-800 text-xs">http://localhost:3001/api/v1</code>
                </p>
            </div>
        </div>
    );
}
