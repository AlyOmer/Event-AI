"use client";

import React, { useState } from "react";
import { Save } from "lucide-react";

export default function SettingsPage() {
    const [settings, setSettings] = useState({
        currency: "PKR",
        taxRate: 16,
        platformFee: 5,
        emailNotifications: true,
        smsNotifications: true,
    });

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        // Settings API not yet implemented
        alert("Settings management is coming soon. Changes are not saved.");
    };

    return (
        <div className="p-8">
            <h1 className="text-2xl font-bold mb-6">Platform Settings</h1>

            <form onSubmit={handleSave} className="bg-white rounded-lg shadow p-6 max-w-2xl">
                <div className="space-y-6">
                    <div>
                        <h3 className="text-lg font-medium mb-4">Financial Configuration</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Currency Support
                                </label>
                                <select
                                    value={settings.currency}
                                    onChange={e => setSettings({ ...settings, currency: e.target.value })}
                                    className="w-full p-2 border rounded-md"
                                >
                                    <option value="PKR">Pakistani Rupee (PKR)</option>
                                    <option value="USD">US Dollar (USD)</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Platform Fee (%)
                                </label>
                                <input
                                    type="number"
                                    value={settings.platformFee}
                                    onChange={e => setSettings({ ...settings, platformFee: Number(e.target.value) })}
                                    className="w-full p-2 border rounded-md"
                                />
                            </div>
                        </div>
                    </div>

                    <div className="border-t pt-4">
                        <h3 className="text-lg font-medium mb-4">Notifications</h3>
                        <div className="space-y-3">
                            <label className="flex items-center space-x-2">
                                <input
                                    type="checkbox"
                                    checked={settings.emailNotifications}
                                    onChange={e => setSettings({ ...settings, emailNotifications: e.target.checked })}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700">Enable Email Notifications</span>
                            </label>
                            <label className="flex items-center space-x-2">
                                <input
                                    type="checkbox"
                                    checked={settings.smsNotifications}
                                    onChange={e => setSettings({ ...settings, smsNotifications: e.target.checked })}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700">Enable SMS Notifications</span>
                            </label>
                        </div>
                    </div>

                    <div className="pt-4">
                        <button
                            type="submit"
                            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 flex items-center gap-2"
                        >
                            <Save className="w-4 h-4" />
                            Save Changes
                        </button>
                        <p className="text-xs text-gray-400 mt-2">Note: Settings backend is not yet connected.</p>
                    </div>
                </div>
            </form>
        </div>
    );
}
