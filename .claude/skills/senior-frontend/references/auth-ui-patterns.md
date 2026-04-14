# Auth UI Patterns Reference

## Google OAuth Button (SVG inline, no external dep)

```tsx
function GoogleButton({ onClick, loading }: { onClick: () => void; loading?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full flex items-center justify-center gap-3 rounded-xl border border-gray-200
                 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm
                 hover:bg-gray-50 hover:border-gray-300 hover:shadow
                 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed
                 transition-all duration-150"
    >
      {loading ? (
        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
      ) : (
        <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
      )}
      {loading ? "Connecting..." : "Continue with Google"}
    </button>
  );
}
```

## next-auth v5 Integration (packages/user)

```tsx
// app/api/auth/[...nextauth]/route.ts
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account?.provider === "google") {
        token.googleId = profile?.sub;
      }
      return token;
    },
    async session({ session, token }) {
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
});

export const { GET, POST } = handlers;
```

```tsx
// In login page — trigger Google sign-in
import { signIn } from "next-auth/react";

<GoogleButton onClick={() => signIn("google", { callbackUrl: "/dashboard" })} />
```

## Auth Page Layout (two-column for desktop)

```tsx
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left: Branding Panel */}
      <div className="hidden lg:flex flex-col justify-between bg-gradient-to-br from-indigo-600 to-purple-700 p-12 text-white">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
            <Calendar className="h-5 w-5 text-white" />
          </div>
          <span className="text-xl font-bold">Event-AI</span>
        </div>

        <div>
          <blockquote className="text-2xl font-semibold leading-relaxed">
            "Plan your perfect event with AI-powered vendor recommendations."
          </blockquote>
          <div className="mt-6 flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-white/20" />
            <div>
              <p className="font-semibold">Sarah Ahmed</p>
              <p className="text-sm text-indigo-200">Wedding Planner, Lahore</p>
            </div>
          </div>
        </div>

        {/* Decorative circles */}
        <div className="absolute bottom-0 right-0 -mb-16 -mr-16 h-64 w-64 rounded-full bg-white/5" />
        <div className="absolute top-1/2 right-8 h-32 w-32 rounded-full bg-white/5" />
      </div>

      {/* Right: Form */}
      <div className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
```

## Password Strength Indicator

```tsx
function PasswordStrength({ password }: { password: string }) {
  const strength = getStrength(password); // 0-4
  const labels = ["", "Weak", "Fair", "Good", "Strong"];
  const colors = ["", "bg-red-500", "bg-yellow-500", "bg-blue-500", "bg-green-500"];

  if (!password) return null;

  return (
    <div className="mt-2 space-y-1.5">
      <div className="flex gap-1">
        {[1, 2, 3, 4].map((level) => (
          <div
            key={level}
            className={cn(
              "h-1 flex-1 rounded-full transition-all duration-300",
              strength >= level ? colors[strength] : "bg-gray-200"
            )}
          />
        ))}
      </div>
      <p className={cn("text-xs font-medium", strength >= 3 ? "text-green-600" : "text-gray-500")}>
        {labels[strength]}
      </p>
    </div>
  );
}

function getStrength(password: string): number {
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;
  return score;
}
```

## Social Proof Strip (below auth form)

```tsx
<div className="mt-8 flex items-center justify-center gap-6 text-xs text-gray-400">
  <div className="flex items-center gap-1.5">
    <Shield className="h-3.5 w-3.5 text-green-500" />
    <span>SSL Secured</span>
  </div>
  <div className="flex items-center gap-1.5">
    <Lock className="h-3.5 w-3.5 text-indigo-500" />
    <span>Privacy Protected</span>
  </div>
  <div className="flex items-center gap-1.5">
    <Users className="h-3.5 w-3.5 text-blue-500" />
    <span>10k+ Users</span>
  </div>
</div>
```

## Error / Status Banners

```tsx
// Error
{error && (
  <div className="flex items-start gap-3 rounded-xl bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-700">
    <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-red-500" />
    <span>{error}</span>
  </div>
)}

// Success
{success && (
  <div className="flex items-start gap-3 rounded-xl bg-green-50 border border-green-100 px-4 py-3 text-sm text-green-700">
    <CheckCircle className="h-4 w-4 mt-0.5 shrink-0 text-green-500" />
    <span>{success}</span>
  </div>
)}

// Info / Pending
{pending && (
  <div className="flex items-start gap-3 rounded-xl bg-amber-50 border border-amber-100 px-4 py-3 text-sm text-amber-700">
    <Clock className="h-4 w-4 mt-0.5 shrink-0 text-amber-500" />
    <span>Your account is pending admin approval.</span>
  </div>
)}
```
