import axios from "axios";
import { getSession, signOut } from "next-auth/react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001/api/v1";

export const api = axios.create({
    baseURL: API_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

// Attach JWT token from NextAuth session to every request
api.interceptors.request.use(async (config) => {
    const session = await getSession();
    if (session && (session as any).accessToken) {
        config.headers.Authorization = `Bearer ${(session as any).accessToken}`;
    }
    return config;
});

// Handle 401 errors — sign out and redirect to login
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Session expired or token invalid — sign out
            await signOut({ callbackUrl: "/login" });
        }
        return Promise.reject(error);
    }
);

export const getVendors = async () => {
    const response = await api.get("/admin/vendors");
    return response.data?.data || response.data;
};

export const updateVendorStatus = async (id: string, status: string) => {
    const response = await api.patch(`/admin/vendors/${id}/status`, { status });
    return response.data;
};

export const getUsers = async () => {
    const response = await api.get("/admin/users");
    return response.data?.data || response.data;
};

export const getStats = async () => {
    const response = await api.get("/admin/stats");
    return response.data?.data || response.data;
};

export const getBookings = async (params?: { page?: number; status?: string }) => {
    const response = await api.get("/bookings", { params: { page: 1, limit: 20, ...params } });
    return response.data?.data || response.data;
};

export const updateBookingStatus = async (id: string, status: "confirmed" | "rejected", reason?: string) => {
    const response = await api.patch(`/bookings/${id}/status`, { status, reason });
    return response.data;
};
