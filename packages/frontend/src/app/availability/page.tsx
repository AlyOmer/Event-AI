"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
    Calendar,
    Clock,
    CheckCircle,
    XCircle,
    AlertCircle,
    Loader2,
    ChevronLeft,
    ChevronRight,
    Filter
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/auth-store";

interface AvailabilityEntry {
    id?: string;
    date: string;
    startTime?: string;
    endTime?: string;
    status: "available" | "booked" | "blocked" | "tentative";
    notes?: string;
    blockedReason?: string;
    serviceId?: string;
    serviceName?: string;
    bookingEventName?: string;
}

interface Service {
    id: string;
    name: string;
}

const STATUS_COLORS = {
    available: "bg-green-100 text-green-800 border-green-200",
    booked: "bg-blue-100 text-blue-800 border-blue-200",
    blocked: "bg-red-100 text-red-800 border-red-200",
    tentative: "bg-yellow-100 text-yellow-800 border-yellow-200",
};

const STATUS_LABELS = {
    available: "Available",
    booked: "Booked",
    blocked: "Blocked",
    tentative: "Tentative",
};

export default function AvailabilityPage() {
    const router = useRouter();
    const { isAuthenticated } = useAuthStore();
    const queryClient = useQueryClient();
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [selectedDate, setSelectedDate] = useState<string | null>(null);
    const [filterService, setFilterService] = useState<string>("");
    const [hasMounted, setHasMounted] = useState(false);

    useEffect(() => {
        setHasMounted(true);
    }, []);

    useEffect(() => {
        if (hasMounted && !isAuthenticated) {
            router.push('/login');
        }
    }, [hasMounted, isAuthenticated, router]);

    // Get date range for current month view
    const startDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
    const endDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);

    // Fetch services
    const { data: services } = useQuery({
        queryKey: ["services"],
        queryFn: async () => {
            const response = await api.get("/vendors/me/services");
            return response.data?.data || [];
        },
    });

    // Fetch availability
    const { data: availability, isLoading } = useQuery({
        queryKey: ["availability", startDate.toISOString(), endDate.toISOString(), filterService],
        queryFn: async () => {
            const response = await api.get("/vendors/me/availability", {
                params: {
                    startDate: startDate.toISOString().split("T")[0],
                    endDate: endDate.toISOString().split("T")[0],
                    serviceId: filterService || undefined,
                },
            });
            return response.data?.data || [];
        },
    });

    // Update availability mutation
    const updateMutation = useMutation({
        mutationFn: async (data: AvailabilityEntry) => {
            const response = await api.post("/vendors/me/availability", data);
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["availability"] });
        },
    });

    // Bulk update mutation
    const bulkUpdateMutation = useMutation({
        mutationFn: async (entries: AvailabilityEntry[]) => {
            const response = await api.post("/vendors/me/availability/bulk", { entries });
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["availability"] });
        },
    });

    const getDaysInMonth = () => {
        const days = [];
        const firstDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
        const lastDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);

        // Add empty cells for days before the first day of the month
        for (let i = 0; i < firstDay.getDay(); i++) {
            days.push(null);
        }

        // Add all days of the month
        for (let i = 1; i <= lastDay.getDate(); i++) {
            days.push(i);
        }

        return days;
    };

    const getAvailabilityForDate = (day: number): AvailabilityEntry[] => {
        if (!availability) return [];
        const dateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        return availability.filter((a: AvailabilityEntry) => a.date === dateStr);
    };

    const getStatusForDate = (day: number): string | null => {
        const entries = getAvailabilityForDate(day);
        if (entries.length === 0) return null;

        // Priority: booked > blocked > tentative > available
        if (entries.some(e => e.status === "booked")) return "booked";
        if (entries.some(e => e.status === "blocked")) return "blocked";
        if (entries.some(e => e.status === "tentative")) return "tentative";
        return "available";
    };

    const handlePrevMonth = () => {
        setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
    };

    const handleNextMonth = () => {
        setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
    };

    const handleDateClick = (day: number) => {
        const dateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        setSelectedDate(dateStr);
    };

    const handleStatusChange = (status: AvailabilityEntry["status"], notes?: string) => {
        if (!selectedDate) return;

        updateMutation.mutate({
            date: selectedDate,
            status,
            notes,
            serviceId: filterService || undefined,
        });

        setSelectedDate(null);
    };

    const monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Availability Calendar</h1>
                <div className="flex items-center gap-4">
                    {/* Service Filter */}
                    <div className="flex items-center gap-2">
                        <Filter className="h-4 w-4 text-surface-500" />
                        <select
                            value={filterService}
                            onChange={(e) => setFilterService(e.target.value)}
                            className="text-sm border-surface-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                        >
                            <option value="">All Services</option>
                            {services?.map((service: Service) => (
                                <option key={service.id} value={service.id}>
                                    {service.name}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* Calendar */}
            <div className="bg-white rounded-xl border border-surface-200 shadow-sm">
                {/* Calendar Header */}
                <div className="p-4 border-b border-surface-200 flex items-center justify-between">
                    <button
                        onClick={handlePrevMonth}
                        className="p-2 hover:bg-surface-100 rounded-lg transition-colors"
                    >
                        <ChevronLeft className="h-5 w-5" />
                    </button>
                    <h2 className="text-xl font-semibold">
                        {monthNames[currentMonth.getMonth()]} {currentMonth.getFullYear()}
                    </h2>
                    <button
                        onClick={handleNextMonth}
                        className="p-2 hover:bg-surface-100 rounded-lg transition-colors"
                    >
                        <ChevronRight className="h-5 w-5" />
                    </button>
                </div>

                {/* Calendar Grid */}
                <div className="p-4">
                    {/* Day Headers */}
                    <div className="grid grid-cols-7 gap-2 mb-2">
                        {dayNames.map(day => (
                            <div key={day} className="text-center text-sm font-medium text-surface-500 py-2">
                                {day}
                            </div>
                        ))}
                    </div>

                    {/* Calendar Days */}
                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="h-8 w-8 animate-spin text-surface-400" />
                        </div>
                    ) : (
                        <div className="grid grid-cols-7 gap-2">
                            {getDaysInMonth().map((day, index) => {
                                if (day === null) {
                                    return <div key={`empty-${index}`} className="h-24" />;
                                }

                                const status = getStatusForDate(day);
                                const entries = getAvailabilityForDate(day);
                                const isToday = new Date().toDateString() ===
                                    new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day).toDateString();

                                return (
                                    <button
                                        key={day}
                                        onClick={() => handleDateClick(day)}
                                        className={cn(
                                            "h-24 p-2 border rounded-lg text-left transition-all hover:shadow-md",
                                            status ? STATUS_COLORS[status as keyof typeof STATUS_COLORS] : "bg-white border-surface-200",
                                            isToday && "ring-2 ring-primary-500",
                                            selectedDate === `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}` && "ring-2 ring-primary-600"
                                        )}
                                    >
                                        <div className="font-semibold text-sm">{day}</div>
                                        {entries.length > 0 && (
                                            <div className="mt-1 text-xs">
                                                {entries.map((entry, i) => (
                                                    <div key={i} className="truncate">
                                                        {entry.startTime && `${entry.startTime.slice(0, 5)} `}
                                                        {STATUS_LABELS[entry.status]}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Legend */}
                <div className="px-4 py-3 border-t border-surface-200 bg-surface-50">
                    <div className="flex flex-wrap gap-4">
                        {Object.entries(STATUS_LABELS).map(([status, label]) => (
                            <div key={status} className="flex items-center gap-2">
                                <div className={cn("w-3 h-3 rounded-full", STATUS_COLORS[status as keyof typeof STATUS_COLORS].split(" ")[0])} />
                                <span className="text-sm text-surface-600">{label}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Selected Date Modal */}
            {selectedDate && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4">
                        <div className="p-4 border-b border-surface-200 flex items-center justify-between">
                            <h3 className="font-semibold text-lg">
                                {new Date(selectedDate).toLocaleDateString("en-US", {
                                    weekday: "long",
                                    year: "numeric",
                                    month: "long",
                                    day: "numeric"
                                })}
                            </h3>
                            <button
                                onClick={() => setSelectedDate(null)}
                                className="p-2 hover:bg-surface-100 rounded-lg"
                            >
                                <XCircle className="h-5 w-5 text-surface-500" />
                            </button>
                        </div>

                        <div className="p-4 space-y-4">
                            <p className="text-surface-600">Set availability status:</p>

                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    onClick={() => handleStatusChange("available")}
                                    disabled={updateMutation.isPending}
                                    className="flex items-center gap-3 p-3 border border-green-200 bg-green-50 rounded-lg hover:bg-green-100 transition-colors text-left"
                                >
                                    <CheckCircle className="h-5 w-5 text-green-600" />
                                    <div>
                                        <div className="font-medium text-green-900">Available</div>
                                        <div className="text-xs text-green-700">Open for bookings</div>
                                    </div>
                                </button>

                                <button
                                    onClick={() => handleStatusChange("blocked")}
                                    disabled={updateMutation.isPending}
                                    className="flex items-center gap-3 p-3 border border-red-200 bg-red-50 rounded-lg hover:bg-red-100 transition-colors text-left"
                                >
                                    <XCircle className="h-5 w-5 text-red-600" />
                                    <div>
                                        <div className="font-medium text-red-900">Blocked</div>
                                        <div className="text-xs text-red-700">Not available</div>
                                    </div>
                                </button>

                                <button
                                    onClick={() => handleStatusChange("tentative")}
                                    disabled={updateMutation.isPending}
                                    className="flex items-center gap-3 p-3 border border-yellow-200 bg-yellow-50 rounded-lg hover:bg-yellow-100 transition-colors text-left"
                                >
                                    <AlertCircle className="h-5 w-5 text-yellow-600" />
                                    <div>
                                        <div className="font-medium text-yellow-900">Tentative</div>
                                        <div className="text-xs text-yellow-700">Hold for possible booking</div>
                                    </div>
                                </button>

                                <button
                                    onClick={() => handleStatusChange("booked")}
                                    disabled={true}
                                    className="flex items-center gap-3 p-3 border border-blue-200 bg-blue-50 rounded-lg opacity-50 cursor-not-allowed text-left"
                                >
                                    <Calendar className="h-5 w-5 text-blue-600" />
                                    <div>
                                        <div className="font-medium text-blue-900">Booked</div>
                                        <div className="text-xs text-blue-700">Already confirmed</div>
                                    </div>
                                </button>
                            </div>

                            {updateMutation.isPending && (
                                <div className="flex items-center justify-center py-2">
                                    <Loader2 className="h-5 w-5 animate-spin text-primary-500" />
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Current Availability List */}
            <div className="bg-white rounded-xl border border-surface-200 shadow-sm">
                <div className="p-4 border-b border-surface-200">
                    <h3 className="font-semibold text-surface-900">Upcoming Availability</h3>
                </div>

                {availability?.length > 0 ? (
                    <div className="divide-y divide-surface-200">
                        {availability
                            .filter((a: AvailabilityEntry) => new Date(a.date) >= new Date())
                            .sort((a: AvailabilityEntry, b: AvailabilityEntry) =>
                                new Date(a.date).getTime() - new Date(b.date).getTime()
                            )
                            .slice(0, 10)
                            .map((entry: AvailabilityEntry) => (
                                <div key={entry.id} className="p-4 flex items-center justify-between hover:bg-surface-50">
                                    <div className="flex items-center gap-3">
                                        <div className={cn(
                                            "w-2 h-2 rounded-full",
                                            entry.status === "available" && "bg-green-500",
                                            entry.status === "booked" && "bg-blue-500",
                                            entry.status === "blocked" && "bg-red-500",
                                            entry.status === "tentative" && "bg-yellow-500"
                                        )} />
                                        <div>
                                            <p className="font-medium text-surface-900">
                                                {new Date(entry.date).toLocaleDateString("en-US", {
                                                    weekday: "short",
                                                    month: "short",
                                                    day: "numeric"
                                                })}
                                            </p>
                                            {entry.serviceName && (
                                                <p className="text-sm text-surface-500">{entry.serviceName}</p>
                                            )}
                                            {entry.notes && (
                                                <p className="text-sm text-surface-500">{entry.notes}</p>
                                            )}
                                        </div>
                                    </div>
                                    <span className={cn(
                                        "px-2.5 py-0.5 rounded-full text-xs font-medium",
                                        STATUS_COLORS[entry.status]
                                    )}>
                                        {STATUS_LABELS[entry.status]}
                                    </span>
                                </div>
                            ))}
                    </div>
                ) : (
                    <div className="p-8 text-center text-surface-500">
                        <Calendar className="mx-auto h-12 w-12 mb-4 opacity-50" />
                        <p>No availability set for this period.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
