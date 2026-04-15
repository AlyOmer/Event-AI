"use client";

import { useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Calendar } from "lucide-react";

/**
 * OAuth callback handler for the user portal.
 *
 * After a successful Google OAuth flow the backend redirects to:
 *   {origin}/auth/callback?token=<access_jwt>&refresh_token=<refresh_token>
 *
 * This page:
 *   1. Reads token + refresh_token from the URL search params
 *   2. Persists them using the same contract as the login page:
 *      - localStorage: "userToken", "userData"
 *      - cookie: "userToken" (used by Next.js middleware for route protection)
 *   3. Fetches /auth/me to populate userData
 *   4. Redirects to /dashboard
 *
 * Error path:
 *   If the backend redirected with ?error=<code>, display a user-friendly
 *   message and redirect to /login.
 *
 * References:
 *   - Backend callback:  packages/backend/src/api/v1/auth.py:516-528
 *   - Login token store: packages/user/src/app/login/page.tsx:65-68
 *   - Middleware guard:   packages/user/src/middleware.ts:34
 */

const ERROR_MESSAGES: Record<string, string> = {
    google_auth_denied: "Google sign-in was cancelled.",
    oauth_email_not_verified: "Your Google email is not verified.",
    auth_account_inactive: "Your account has been deactivated. Contact support.",
    invalid_callback: "Invalid sign-in callback. Please try again.",
    oauth_invalid_state: "Sign-in session expired. Please try again.",
    oauth_token_exchange_failed: "Google sign-in failed. Please try again.",
    oauth_not_configured: "Google sign-in is not available right now.",
};

function CallbackHandler() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const handled = useRef(false);

    const API_URL =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";

    useEffect(() => {
        // Guard against React strict-mode double-invocation
        if (handled.current) return;
        handled.current = true;

        const token = searchParams.get("token");
        const refreshToken = searchParams.get("refresh_token");
        const error = searchParams.get("error");

        // ── Error redirect from backend ──────────────────────────────────
        if (error) {
            const msg = encodeURIComponent(
                ERROR_MESSAGES[error] ?? "Google sign-in failed. Please try again."
            );
            router.replace(`/login?error=${msg}`);
            return;
        }

        // ── Missing tokens — invalid direct navigation ───────────────────
        if (!token || !refreshToken) {
            router.replace(
                "/login?error=" +
                    encodeURIComponent("Missing authentication tokens. Please try again.")
            );
            return;
        }

        // ── Persist tokens (same contract as login page) ─────────────────
        // localStorage: userToken (used by api.ts interceptor)
        localStorage.setItem("userToken", token);
        // cookie: userToken (used by Next.js middleware.ts for auth gating)
        document.cookie = `userToken=${token}; path=/; max-age=604800; SameSite=Lax`;

        // ── Fetch user profile to populate userData ──────────────────────
        fetch(`${API_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((res) => {
                if (!res.ok) throw new Error("Failed to fetch profile");
                return res.json();
            })
            .then((data) => {
                // The /auth/me response follows the User model shape
                localStorage.setItem("userData", JSON.stringify(data));
                router.replace("/dashboard");
            })
            .catch(() => {
                // Even if profile fetch fails, tokens are stored — redirect anyway
                router.replace("/dashboard");
            });
    }, [searchParams, router, API_URL]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="flex flex-col items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg">
                    <Calendar className="h-6 w-6 text-white" />
                </div>
                <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                <p className="text-sm text-gray-500">Completing sign-in…</p>
            </div>
        </div>
    );
}

export default function AuthCallbackPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen flex items-center justify-center bg-gray-50">
                    <div className="flex flex-col items-center gap-3">
                        <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                            <Calendar className="h-5 w-5 text-white" />
                        </div>
                        <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                    </div>
                </div>
            }
        >
            <CallbackHandler />
        </Suspense>
    );
}
