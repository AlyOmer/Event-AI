import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PROTECTED_PATHS = ['/dashboard', '/bookings', '/services', '/availability', '/profile'];
const PUBLIC_ONLY_PATHS = ['/login', '/register', '/forgot-password', '/reset-password'];

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    const isAuthenticated = request.cookies.get('is-authenticated')?.value === 'true';
    const userRole = request.cookies.get('user-role')?.value;

    const isProtected = PROTECTED_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'));
    const isPublicOnly = PUBLIC_ONLY_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'));

    if (isProtected && !isAuthenticated) {
        const loginUrl = new URL('/login', request.url);
        loginUrl.searchParams.set('from', pathname);
        return NextResponse.redirect(loginUrl);
    }

    // Vendor portal requires vendor role — redirect non-vendors to register page
    if (isProtected && isAuthenticated && userRole && userRole !== 'vendor' && userRole !== 'admin') {
        return NextResponse.redirect(new URL('/register', request.url));
    }

    if (isPublicOnly && isAuthenticated) {
        return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        '/dashboard/:path*',
        '/bookings/:path*',
        '/services/:path*',
        '/availability/:path*',
        '/profile/:path*',
        '/login',
        '/register',
        '/forgot-password',
        '/reset-password',
    ],
};
