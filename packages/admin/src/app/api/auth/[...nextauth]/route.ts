import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001/api/v1";

// Roles allowed to access the admin portal
const ALLOWED_ROLES = ["admin", "owner"];

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        try {
          const res = await fetch(`${API_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials?.email,
              password: credentials?.password,
            }),
          });

          if (!res.ok) return null;

          const data = await res.json();

          // RBAC: Only allow admin/owner roles into the admin portal
          const userRole = data.user?.role?.toLowerCase();
          if (!userRole || !ALLOWED_ROLES.includes(userRole)) {
            // Reject login for non-admin users
            return null;
          }

          return {
            id: data.user?.id || "1",
            name: `${data.user?.firstName || ""} ${data.user?.lastName || ""}`.trim() || "Admin",
            email: data.user?.email || (credentials?.email as string),
            accessToken: data.accessToken,
            role: userRole,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = (user as any).accessToken;
        token.role = (user as any).role;
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).accessToken = token.accessToken;
      (session as any).role = token.role;
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
});

export const { GET, POST } = handlers;
