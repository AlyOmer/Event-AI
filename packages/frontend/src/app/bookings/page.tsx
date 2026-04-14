'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Calendar, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { api, getApiError } from '@/lib/api';

interface Booking {
    id: string;
    event_name: string;
    client_name: string;
    service_id: string;
    event_date: string;
    status: 'pending' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'rejected';
    total_price: number;
    currency: string;
}

const statusColors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    confirmed: 'bg-blue-100 text-blue-800',
    in_progress: 'bg-purple-100 text-purple-800',
    completed: 'bg-green-100 text-green-800',
    cancelled: 'bg-red-100 text-red-800',
    rejected: 'bg-gray-100 text-gray-800',
};

export default function BookingsPage() {
    const router = useRouter();
    const { isAuthenticated } = useAuthStore();
    const [bookings, setBookings] = useState<Booking[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState('all');
    const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
    const [hasMounted, setHasMounted] = useState(false);

    useEffect(() => { setHasMounted(true); }, []);

    useEffect(() => {
        if (hasMounted && !isAuthenticated) router.push('/login');
    }, [hasMounted, isAuthenticated, router]);

    useEffect(() => {
        if (!hasMounted || !isAuthenticated) return;
        api.get('/vendors/me/bookings')
            .then(r => setBookings(r.data.data || []))
            .catch(err => setError(getApiError(err)))
            .finally(() => setLoading(false));
    }, [hasMounted, isAuthenticated]);

    const handleAction = async (bookingId: string, action: 'confirmed' | 'rejected') => {
        let reason: string | null = null;
        if (action === 'rejected') {
            reason = window.prompt('Reason for rejection (optional):');
        }
        setActionLoading(prev => ({ ...prev, [bookingId]: true }));
        try {
            const res = await api.patch(`/vendors/me/bookings/${bookingId}/status`, { status: action, reason });
            setBookings(prev => prev.map(b => b.id === bookingId ? { ...b, status: res.data.data.status } : b));
        } catch (err: any) {
            alert(getApiError(err));
        } finally {
            setActionLoading(prev => ({ ...prev, [bookingId]: false }));
        }
    };

    if (!hasMounted || !isAuthenticated) return <div className="flex min-h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary-600" /></div>;

    const filtered = bookings.filter(b => statusFilter === 'all' || b.status === statusFilter);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-gray-900">Bookings</h1>
                <p className="text-gray-500 mt-1">Manage your event bookings and reservations</p>
            </div>

            <div className="flex gap-2 flex-wrap">
                {['all', 'pending', 'confirmed', 'in_progress', 'completed', 'cancelled'].map(s => (
                    <button key={s} onClick={() => setStatusFilter(s)}
                        className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                            statusFilter === s ? 'bg-primary-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
                        }`}>
                        {s === 'all' ? 'All' : s.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </button>
                ))}
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-primary-600" /></div>
                ) : error ? (
                    <div className="text-center py-20"><p className="text-red-500">{error}</p></div>
                ) : filtered.length === 0 ? (
                    <div className="text-center py-20">
                        <Calendar className="mx-auto h-12 w-12 text-gray-300 mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-1">No bookings yet</h3>
                        <p className="text-gray-500">Bookings will appear here when customers make reservations</p>
                    </div>
                ) : (
                    <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Event</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Client</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Date</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase">Amount</th>
                                <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {filtered.map(booking => (
                                <tr key={booking.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{booking.event_name || '—'}</td>
                                    <td className="px-6 py-4 text-sm text-gray-600">{booking.client_name || '—'}</td>
                                    <td className="px-6 py-4 text-sm text-gray-600">{new Date(booking.event_date).toLocaleDateString()}</td>
                                    <td className="px-6 py-4">
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[booking.status] || 'bg-gray-100 text-gray-800'}`}>
                                            {booking.status.replace('_', ' ')}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-900 text-right font-medium">
                                        {booking.currency} {booking.total_price?.toLocaleString()}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        {booking.status === 'pending' && (
                                            <div className="flex justify-end gap-2">
                                                <button
                                                    onClick={() => handleAction(booking.id, 'confirmed')}
                                                    disabled={actionLoading[booking.id]}
                                                    className="px-3 py-1 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-1"
                                                >
                                                    {actionLoading[booking.id] ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                                                    Confirm
                                                </button>
                                                <button
                                                    onClick={() => handleAction(booking.id, 'rejected')}
                                                    disabled={actionLoading[booking.id]}
                                                    className="px-3 py-1 text-xs font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-1"
                                                >
                                                    {actionLoading[booking.id] ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                                                    Reject
                                                </button>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
