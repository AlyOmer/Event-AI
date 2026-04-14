"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Loader2, ArrowRight, ArrowLeft } from "lucide-react";
import { cn } from "@repo/ui/lib/utils";
import { createEvent } from "@/lib/api";
import { useRouter } from "next/navigation";

const eventSchema = z.object({
    eventType: z.string().min(1, "Event type is required"),
    date: z.string().min(1, "Date is required"),
    attendees: z.number().min(1, "At least 1 attendee required"),
    budget: z.number().min(100, "Minimum budget is 100"),
    location: z.string().min(1, "Location is required"),
    description: z.string().optional(),
});

type EventFormValues = z.infer<typeof eventSchema>;

export default function CreateEventPage() {
    const router = useRouter();
    const [step, setStep] = useState(1);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const form = useForm<EventFormValues>({
        resolver: zodResolver(eventSchema),
        defaultValues: {
            eventType: "",
            attendees: 50,
            budget: 5000,
            location: "",
        },
    });

    const onSubmit = async (data: EventFormValues) => {
        setIsSubmitting(true);
        setError(null);

        try {
            // Map form data to API format
            const eventData = {
                eventType: data.eventType,
                eventName: `${data.eventType.charAt(0).toUpperCase() + data.eventType.slice(1)} Event`,
                eventDate: data.date,
                location: data.location,
                attendees: data.attendees,
                budget: data.budget,
                preferences: data.description ? [data.description] : [],
            };

            const result = await createEvent(eventData);

            // Redirect to dashboard or event details
            if (result?.event?.id) {
                router.push(`/dashboard?eventId=${result.event.id}`);
            } else {
                router.push("/dashboard");
            }
        } catch (err: any) {
            console.error("Failed to create event:", err);
            setError(err?.response?.data?.error || "Failed to create event. Please try again.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const nextStep = async () => {
        const fields = step === 1
            ? ["eventType", "date", "attendees"] as const
            : ["budget", "location", "description"] as const;

        const isValid = await form.trigger(fields);
        if (isValid) setStep(step + 1);
    };

    return (
        <div className="max-w-2xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Create New Event</h1>
                <p className="mt-2 text-sm text-gray-600">Let's plan your perfect event together.</p>
            </div>

            <div className="bg-white shadow rounded-lg p-8">
                {/* Progress Bar */}
                <div className="mb-8">
                    <div className="h-2 bg-gray-200 rounded-full">
                        <div
                            className="h-2 bg-indigo-600 rounded-full transition-all duration-300"
                            style={{ width: `${(step / 2) * 100}%` }}
                        />
                    </div>
                    <div className="flex justify-between mt-2 text-xs text-gray-500">
                        <span>Basic Details</span>
                        <span>Preferences</span>
                    </div>
                </div>

                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    {/* Error Message */}
                    {error && (
                        <div className="rounded-md bg-red-50 p-4">
                            <p className="text-sm text-red-700">{error}</p>
                        </div>
                    )}

                    {step === 1 && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Event Type</label>
                                <select
                                    {...form.register("eventType")}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                >
                                    <option value="">Select type...</option>
                                    <option value="wedding">Wedding</option>
                                    <option value="corporate">Corporate</option>
                                    <option value="birthday">Birthday</option>
                                    <option value="other">Other</option>
                                </select>
                                {form.formState.errors.eventType && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.eventType.message}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Date</label>
                                <input
                                    type="date"
                                    {...form.register("date")}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                />
                                {form.formState.errors.date && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.date.message}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Estimated Attendees</label>
                                <input
                                    type="number"
                                    {...form.register("attendees", { valueAsNumber: true })}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                />
                                {form.formState.errors.attendees && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.attendees.message}</p>
                                )}
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Budget (PKR)</label>
                                <input
                                    type="number"
                                    {...form.register("budget", { valueAsNumber: true })}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                />
                                {form.formState.errors.budget && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.budget.message}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Location / City</label>
                                <input
                                    type="text"
                                    {...form.register("location")}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                />
                                {form.formState.errors.location && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.location.message}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Additional Description</label>
                                <textarea
                                    {...form.register("description")}
                                    rows={4}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                    placeholder="Describe your vision..."
                                />
                            </div>
                        </div>
                    )}

                    <div className="flex justify-between pt-4">
                        {step > 1 ? (
                            <button
                                type="button"
                                onClick={() => setStep(step - 1)}
                                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                            >
                                <ArrowLeft className="mr-2 h-4 w-4" /> Back
                            </button>
                        ) : (
                            <div /> // Spacer
                        )}

                        {step < 2 ? (
                            <button
                                type="button"
                                onClick={nextStep}
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                            >
                                Next <ArrowRight className="ml-2 h-4 w-4" />
                            </button>
                        ) : (
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                            >
                                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Create Event
                            </button>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
}
