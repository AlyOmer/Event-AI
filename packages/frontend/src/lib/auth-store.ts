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

// ---- Map backend user shape to frontend User type ----
function _mapUser(u: Record<string, unknown>): User {
    return {
        id: u.id as string,
        email: u.email as string,
        firstName: (u.first_name ?? u.firstName ?? null) as string | null,
        lastName: (u.last_name ?? u.lastName ?? null) as string | null,
        role: (u.role as User['role']) ?? 'owner',
        phone: (u.phone ?? null) as string | null,
        avatarUrl: (u.avatar_url ?? u.avatarUrl ?? null) as string | null,
        twoFactorEnabled: (u.two_factor_enabled ?? u.twoFactorEnabled ?? false) as boolean,
        emailVerified: (u.email_verified ?? u.emailVerified ?? false) as boolean,
    };
}


function setAuthCookie() {
    if (typeof document !== 'undefined') {
        document.cookie = 'is-authenticated=true; path=/; max-age=604800; SameSite=Lax';
    }
}

function clearAuthCookie() {
    if (typeof document !== 'undefined') {
        document.cookie = 'is-authenticated=; path=/; max-age=0; SameSite=Lax';
    }
}

// Types
export interface User {
    id: string;
    email: string;
    firstName: string | null;
    lastName: string | null;
    role: 'owner' | 'admin' | 'staff' | 'readonly';
    phone: string | null;
    avatarUrl: string | null;
    twoFactorEnabled: boolean;
    emailVerified: boolean;
}

export interface Vendor {
    id: string;
    name: string;
    businessType: string | null;
    contactEmail: string;
    phone: string | null;
    address: Record<string, string>;
    description: string | null;
    logoUrl: string | null;
    website: string | null;
    verified: boolean;
    status: 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'DEACTIVATED';
    tier: 'BRONZE' | 'SILVER' | 'GOLD';
    apiEnabled: boolean;
    serviceAreas: string[];
    settings: Record<string, unknown>;
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
                    const { token, refresh_token, user } = response.data.data ?? response.data;
                    setAccessToken(token ?? response.data.accessToken);
                    setRefreshToken(refresh_token ?? response.data.refreshToken);
                    setAuthCookie();
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
                    const response = await api.get('/auth/me');
                    const user = response.data;
                    set({
                        user: _mapUser(user),
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

                    const { token, refresh_token, user } = response.data.data ?? response.data;
                    setAccessToken(token ?? response.data.accessToken);
                    setRefreshToken(refresh_token ?? response.data.refreshToken);
                    setAuthCookie();
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
                    await api.post('/auth/register', data);
                    set({ isLoading: false });
                    return true;
                } catch (error) {
                    set({
                        error: getApiError(error),
                        isLoading: false,
                    });
                    return false;
                }
            },

            logout: async () => {
                try {
                    await api.post('/auth/logout');
                } catch (error) {
                    // Ignore logout errors
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
                    const response = await api.get('/vendors/me');
                    set({
                        user: response.data.user,
                        vendor: response.data.vendor,
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
                    const response = await api.put('/vendors/me', data);
                    set({
                        vendor: { ...get().vendor!, ...response.data },
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
