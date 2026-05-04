import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import api, { setAccessToken, setRefreshToken, clearTokens, getApiError } from './api';

// ---- Secure pending credentials store (module-scoped, never persisted) ----
let _pendingCredentials: { email: string; password: string } | null = null;
let _pendingTimeout: ReturnType<typeof setTimeout> | null = null;

const PENDING_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

function setPendingCredentials(email: string, password: string) {
    clearPendingCredentials();
    _pendingCredentials = { email, password };
    _pendingTimeout = setTimeout(() => {
        clearPendingCredentials();
    }, PENDING_TIMEOUT_MS);
}

function clearPendingCredentials() {
    _pendingCredentials = null;
    if (_pendingTimeout) {
        clearTimeout(_pendingTimeout);
        _pendingTimeout = null;
    }
}

function getPendingCredentials() {
    return _pendingCredentials;
}

// ---- Map backend user shape (snake_case) to frontend User type (camelCase) ----
export function _mapUser(u: Record<string, unknown>): User {
    return {
        id: u.id as string,
        email: u.email as string,
        firstName: (u.first_name ?? u.firstName ?? null) as string | null,
        lastName: (u.last_name ?? u.lastName ?? null) as string | null,
        role: (u.role as User['role']) ?? 'user',
        phone: (u.phone ?? null) as string | null,
        avatarUrl: (u.avatar_url ?? u.avatarUrl ?? null) as string | null,
        twoFactorEnabled: (u.two_factor_enabled ?? u.twoFactorEnabled ?? false) as boolean,
        emailVerified: (u.email_verified ?? u.emailVerified ?? false) as boolean,
    };
}

// ---- Map backend vendor shape (snake_case) to frontend Vendor type (camelCase) ----
export function _mapVendor(v: Record<string, unknown>): Vendor {
    return {
        id: v.id as string,
        userId: (v.user_id ?? v.userId) as string,
        businessName: (v.business_name ?? v.businessName ?? '') as string,
        description: (v.description ?? null) as string | null,
        contactEmail: (v.contact_email ?? v.contactEmail ?? '') as string,
        contactPhone: (v.contact_phone ?? v.contactPhone ?? null) as string | null,
        website: (v.website ?? null) as string | null,
        logoUrl: (v.logo_url ?? v.logoUrl ?? null) as string | null,
        city: (v.city ?? null) as string | null,
        region: (v.region ?? null) as string | null,
        status: (v.status as Vendor['status']) ?? 'PENDING',
        rating: (v.rating ?? 0) as number,
        totalReviews: (v.total_reviews ?? v.totalReviews ?? 0) as number,
        categories: (v.categories ?? []) as CategoryRead[],
    };
}

function setAuthCookie() {
    if (typeof document !== 'undefined') {
        document.cookie = 'is-authenticated=true; path=/; max-age=604800; SameSite=Lax';
    }
}

function setRoleCookie(role: string) {
    if (typeof document !== 'undefined') {
        document.cookie = `user-role=${role}; path=/; max-age=604800; SameSite=Lax`;
    }
}

function clearAuthCookie() {
    if (typeof document !== 'undefined') {
        document.cookie = 'is-authenticated=; path=/; max-age=0; SameSite=Lax';
        document.cookie = 'user-role=; path=/; max-age=0; SameSite=Lax';
    }
}

// ---- Types ----

export interface CategoryRead {
    id: string;
    name: string;
    slug: string;
}

export interface User {
    id: string;
    email: string;
    firstName: string | null;
    lastName: string | null;
    role: 'user' | 'vendor' | 'admin';
    phone: string | null;
    avatarUrl: string | null;
    twoFactorEnabled: boolean;
    emailVerified: boolean;
}

export interface Vendor {
    id: string;
    userId: string;
    businessName: string;
    description: string | null;
    contactEmail: string;
    contactPhone: string | null;
    website: string | null;
    logoUrl: string | null;
    city: string | null;
    region: string | null;
    status: 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'REJECTED';
    rating: number;
    totalReviews: number;
    categories: CategoryRead[];
}

interface AuthState {
    user: User | null;
    vendor: Vendor | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
    requiresTwoFactor: boolean;
    pendingEmail: string | null;

    // Actions
    login: (email: string, password: string) => Promise<boolean>;
    loginWithTokens: (token: string, refreshToken: string) => Promise<void>;
    verify2FA: (code: string) => Promise<boolean>;
    register: (data: RegisterData) => Promise<boolean>;
    logout: () => Promise<void>;
    fetchProfile: () => Promise<void>;
    updateProfile: (data: Partial<Vendor>) => Promise<void>;
    clearError: () => void;
}

interface RegisterData {
    vendorName: string;
    businessType?: string;
    contactEmail: string;
    phone?: string;
    website?: string;
    firstName: string;
    lastName: string;
    email: string;
    password: string;
    confirmPassword: string;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            vendor: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
            requiresTwoFactor: false,
            pendingEmail: null,

            login: async (email: string, password: string) => {
                set({ isLoading: true, error: null });
                try {
                    const response = await api.post('/users/login', { email, password });

                    if (response.data.requiresTwoFactor) {
                        setPendingCredentials(email, password);
                        set({
                            requiresTwoFactor: true,
                            pendingEmail: email,
                            isLoading: false,
                        });
                        return false;
                    }

                    // Backend returns { success, data: { token, refresh_token, expires_in, user } }
                    const payload = response.data.data ?? response.data;
                    const { token, refresh_token, user } = payload;
                    setAccessToken(token);
                    setRefreshToken(refresh_token);
                    setAuthCookie();
                    setRoleCookie(user.role ?? 'user');
                    clearPendingCredentials();

                    set({
                        user: _mapUser(user),
                        vendor: null,
                        isAuthenticated: true,
                        isLoading: false,
                        requiresTwoFactor: false,
                        pendingEmail: null,
                    });

                    return true;
                } catch (error) {
                    set({
                        error: getApiError(error),
                        isLoading: false,
                    });
                    return false;
                }
            },

            loginWithTokens: async (token: string, refreshToken: string) => {
                setAccessToken(token);
                setRefreshToken(refreshToken);
                setAuthCookie();
                try {
                    // Fetch user profile after OAuth callback
                    const userResp = await api.get('/users/me');
                    const userData = userResp.data.data ?? userResp.data;
                    setRoleCookie(userData.role ?? 'user');
                    set({
                        user: _mapUser(userData),
                        isAuthenticated: true,
                        isLoading: false,
                    });
                } catch {
                    // tokens may be valid but /me failed — still mark authenticated
                    set({ isAuthenticated: true, isLoading: false });
                }
            },

            verify2FA: async (code: string) => {
                const creds = getPendingCredentials();
                if (!creds) {
                    set({ error: 'Login session expired. Please try again.' });
                    return false;
                }

                set({ isLoading: true, error: null });
                try {
                    const response = await api.post('/auth/login', {
                        email: creds.email,
                        password: creds.password,
                        twoFactorCode: code,
                    });

                    const payload = response.data.data ?? response.data;
                    const { token, refresh_token, user } = payload;
                    setAccessToken(token);
                    setRefreshToken(refresh_token);
                    setAuthCookie();
                    setRoleCookie(user.role ?? 'user');
                    clearPendingCredentials();

                    set({
                        user: _mapUser(user),
                        vendor: null,
                        isAuthenticated: true,
                        isLoading: false,
                        requiresTwoFactor: false,
                        pendingEmail: null,
                    });

                    return true;
                } catch (error) {
                    set({
                        error: getApiError(error),
                        isLoading: false,
                    });
                    return false;
                }
            },

            register: async (data: RegisterData) => {
                set({ isLoading: true, error: null });
                try {
                    // Step 1: create user account with vendor role
                    const regResp = await api.post('/auth/register', {
                        email: data.email,
                        password: data.password,
                        first_name: data.firstName,
                        last_name: data.lastName,
                        role: 'vendor',
                    });
                    const payload = regResp.data.data ?? regResp.data;

                    // Step 2: authenticate with returned tokens
                    if (payload?.access_token) {
                        setAccessToken(payload.access_token);
                        if (payload.refresh_token) setRefreshToken(payload.refresh_token);
                        setAuthCookie();
                        setRoleCookie('vendor');

                        // Step 3: create vendor profile
                        try {
                            await api.post('/vendors/register', {
                                business_name: data.vendorName,
                                contact_email: data.contactEmail || data.email,
                            });
                        } catch {
                            // vendor profile creation failed — not fatal
                        }
                    }

                    set({ isLoading: false });
                    return true;
                } catch (error) {
                    set({ error: getApiError(error), isLoading: false });
                    return false;
                }
            },

            logout: async () => {
                try {
                    await api.post('/auth/logout');
                } catch {
                    // Ignore logout errors — always clear local state
                } finally {
                    clearTokens();
                    clearAuthCookie();
                    clearPendingCredentials();
                    set({
                        user: null,
                        vendor: null,
                        isAuthenticated: false,
                        requiresTwoFactor: false,
                        pendingEmail: null,
                    });
                }
            },

            fetchProfile: async () => {
                set({ isLoading: true });
                try {
                    // Fetch vendor profile from the correct endpoint
                    const response = await api.get('/vendors/profile/me');
                    const vendorData = response.data.data ?? response.data;
                    set({
                        vendor: _mapVendor(vendorData),
                        isLoading: false,
                    });
                } catch (error) {
                    set({
                        error: getApiError(error),
                        isLoading: false,
                    });
                }
            },

            updateProfile: async (data: Partial<Vendor>) => {
                set({ isLoading: true, error: null });
                try {
                    const response = await api.put('/vendors/profile/me', data);
                    const vendorData = response.data.data ?? response.data;
                    set({
                        vendor: _mapVendor(vendorData),
                        isLoading: false,
                    });
                } catch (error) {
                    set({
                        error: getApiError(error),
                        isLoading: false,
                    });
                    throw error;
                }
            },

            clearError: () => set({ error: null }),
        }),
        {
            name: 'auth-storage',
            storage: createJSONStorage(() => localStorage),
            partialize: (state) => ({
                user: state.user,
                vendor: state.vendor,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);

export default useAuthStore;
