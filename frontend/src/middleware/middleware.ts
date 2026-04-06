import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { ROUTES } from '@/routes/routePaths';

// Checks if a path matches or starts with any route
const pathMatches = (path: string, routeMap: Record<string, string>): boolean => {
  return Object.values(routeMap).some(route =>
    path === route || path.startsWith(`${route}/`) ||
    (path.startsWith(route) && path.charAt(route.length) === '?')
  );
};

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const authCookie = request.cookies.get('isAuthenticated')?.value?.trim();
  const isAuthenticated = authCookie === 'true';

  // Rutas importantes
  const dashboardPath = ROUTES.PROTECTED.DASHBOARD;
  const loginPath = ROUTES.PUBLIC.LOGIN;

  if (pathname === loginPath) {
    if (isAuthenticated) {
      return NextResponse.redirect(new URL(dashboardPath, request.url));
    }
    return NextResponse.next();
  }

  if (pathMatches(pathname, ROUTES.PUBLIC)) {
    return NextResponse.next();
  }

  if (!isAuthenticated && (pathMatches(pathname, ROUTES.PROTECTED) || pathMatches(pathname, ROUTES.DOCTOR))) {
    const url = new URL(loginPath, request.url);
    url.searchParams.set('from', pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

// Ejecutar middleware en todas las rutas menos assets y API
export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|public|api).*)',
  ],
};
