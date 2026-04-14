'use client';

import { useState, useEffect, useRef } from 'react';
import { Send, MessageSquare, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

interface Booking {
    id: string;
    event_name: string | null;
    event_date: string;
    status: string;
}

interface Message {
    id: string;
    message: string;
    sender_type: 'client' | 'vendor' | 'system';
    created_at: string;
}

const statusColors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-700',
    confirmed: 'bg-green-100 text-green-700',
    cancelled: 'bg-red-100 text-red-700',
    completed: 'bg-blue-100 text-blue-700',
    rejected: 'bg-gray-100 text-gray-700',
};

export default function MessagesPage() {
    const [bookings, setBookings] = useState<Booking[]>([]);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [text, setText] = useState('');
    const [loadingBookings, setLoadingBookings] = useState(true);
    const [loadingMessages, setLoadingMessages] = useState(false);
    const [sending, setSending] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        api.get('/bookings/')
            .then(r => setBookings(r.data.data || []))
            .finally(() => setLoadingBookings(false));
    }, []);

    useEffect(() => {
        if (!selectedId) return;
        setLoadingMessages(true);
        api.get(`/bookings/${selectedId}/messages`)
            .then(r => setMessages((r.data.data || []).reverse()))
            .finally(() => setLoadingMessages(false));
    }, [selectedId]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async () => {
        if (!text.trim() || !selectedId) return;
        setSending(true);
        try {
            const res = await api.post(`/bookings/${selectedId}/messages`, {
                message: text.trim(),
                sender_type: 'client',
            });
            setMessages(prev => [...prev, res.data]);
            setText('');
        } finally {
            setSending(false);
        }
    };

    const selectedBooking = bookings.find(b => b.id === selectedId);

    return (
        <div className="flex h-[calc(100vh-8rem)] bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            {/* Sidebar */}
            <div className="w-72 border-r border-gray-100 flex flex-col">
                <div className="px-4 py-3 border-b border-gray-100">
                    <h2 className="font-semibold text-gray-900">Booking Messages</h2>
                </div>
                <div className="flex-1 overflow-y-auto">
                    {loadingBookings ? (
                        <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-gray-400" /></div>
                    ) : bookings.length === 0 ? (
                        <p className="text-sm text-gray-400 text-center py-8">No bookings yet</p>
                    ) : bookings.map(b => (
                        <button
                            key={b.id}
                            onClick={() => setSelectedId(b.id)}
                            className={`w-full text-left px-4 py-3 border-b border-gray-50 hover:bg-gray-50 transition-colors ${
                                selectedId === b.id ? 'bg-indigo-50' : ''
                            }`}
                        >
                            <p className="text-sm font-medium text-gray-900 truncate">{b.event_name || 'Booking'}</p>
                            <div className="flex items-center gap-2 mt-1">
                                <span className="text-xs text-gray-400">{new Date(b.event_date).toLocaleDateString()}</span>
                                <span className={`text-xs px-1.5 py-0.5 rounded-full ${statusColors[b.status] || 'bg-gray-100 text-gray-600'}`}>
                                    {b.status}
                                </span>
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Chat area */}
            <div className="flex-1 flex flex-col">
                {!selectedId ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
                        <MessageSquare className="h-12 w-12 mb-3" />
                        <p>Select a booking to view messages</p>
                    </div>
                ) : (
                    <>
                        <div className="px-4 py-3 border-b border-gray-100">
                            <p className="font-medium text-gray-900">{selectedBooking?.event_name || 'Booking'}</p>
                        </div>
                        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
                            {loadingMessages ? (
                                <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-gray-400" /></div>
                            ) : messages.length === 0 ? (
                                <p className="text-sm text-gray-400 text-center py-8">No messages yet. Start the conversation!</p>
                            ) : messages.map(m => (
                                <div key={m.id} className={`flex ${m.sender_type === 'client' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-xs px-4 py-2 rounded-2xl text-sm ${
                                        m.sender_type === 'client'
                                            ? 'bg-indigo-600 text-white rounded-br-sm'
                                            : 'bg-gray-100 text-gray-900 rounded-bl-sm'
                                    }`}>
                                        {m.message}
                                    </div>
                                </div>
                            ))}
                            <div ref={bottomRef} />
                        </div>
                        <div className="px-4 py-3 border-t border-gray-100 flex gap-2">
                            <input
                                value={text}
                                onChange={e => setText(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                                placeholder="Type a message..."
                                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            />
                            <button
                                onClick={sendMessage}
                                disabled={sending || !text.trim()}
                                className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                            >
                                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
