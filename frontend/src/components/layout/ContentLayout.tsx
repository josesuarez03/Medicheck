'use client';

import React, { useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import Loading from "@/components/loading";
import { ROUTES } from "@/routes/routePaths";
import { useAuth } from "@/hooks/useAuth";
import { usePathname, useRouter } from 'next/navigation';

export default function ContentLayout({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, loading } = useAuth();
    const pathname = usePathname();
    const router = useRouter();
    const safePath = pathname || "";
    const isHomeRoute = pathname === ROUTES.PUBLIC.HOME;
    const isAuthRoute = pathname?.startsWith("/auth/");

    // Determinar si es una ruta protegida explícitamente
    const isProtectedRoute = Object.values(ROUTES.PROTECTED).some(route => 
        pathname === route || 
        (pathname && pathname.startsWith(`${route}/`)) ||
        (pathname && pathname.startsWith(route) && pathname.charAt(route.length) === '?')
    );

    // Determinar si es una ruta de doctor explícitamente
    const isDoctorRoute = Object.values(ROUTES.DOCTOR).some(route => 
        pathname === route || 
        (pathname && pathname.startsWith(`${route}/`)) ||
        (pathname && pathname.startsWith(route) && pathname.charAt(route.length) === '?')
    );

    // Solo mostrar el layout completo si está autenticado Y está en una ruta protegida o de doctor
    const shouldShowFullLayout = isAuthenticated && (isProtectedRoute || isDoctorRoute);

    // Handle navigation and auth state
    useEffect(() => {
        if (!loading) {
            // Manejar acceso a rutas protegidas cuando no está autenticado
            if (!isAuthenticated && (isProtectedRoute || isDoctorRoute)) {
                router.push(`${ROUTES.PUBLIC.LOGIN}?from=${encodeURIComponent(safePath)}`);
                return;
            }

        }
    }, [isAuthenticated, isProtectedRoute, isDoctorRoute, loading, pathname, router, safePath]);
    
    // Mostrar componente de carga mientras se determina el estado de autenticación
    if (loading) {
        return <Loading />;
    }

    // Layout completo para usuarios autenticados en rutas no públicas
    if (shouldShowFullLayout) {
        return (
            <div className="flex h-screen bg-gradient-to-b from-slate-100 to-slate-50 dark:from-[#071228] dark:via-[#0B1836] dark:to-[#0E1D40]">
                <a
                    href="#main-content"
                    className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
                >
                    Saltar al contenido principal
                </a>
                <Sidebar />
                <div className="flex flex-col flex-1 overflow-hidden">
                    <Header />
                    <main id="main-content" className="flex-1 overflow-y-auto">
                        <div className="page-container">
                        {children}
                        </div>
                    </main>
                </div>
            </div>
        );
    }

    if (isHomeRoute) {
        return (
            <div className="min-h-screen bg-background">
                <a
                    href="#main-content"
                    className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
                >
                    Saltar al contenido principal
                </a>
                <main id="main-content">{children}</main>
            </div>
        );
    }
      
    // Layout simple para rutas públicas
    return (
        <div className={`min-h-screen ${isAuthRoute ? "auth-shell" : "bg-gradient-to-b from-slate-100 to-slate-50 dark:from-[#071228] dark:via-[#0B1836] dark:to-[#0E1D40]"}`}>
            <main id="main-content" className={`min-h-screen px-4 py-8 ${isAuthRoute ? "flex items-center justify-center" : ""}`}>
                {children}
            </main>
        </div>
    );
}
