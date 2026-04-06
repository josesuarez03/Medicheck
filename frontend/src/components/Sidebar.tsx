"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Button } from "./ui/button";
import {
  TbBriefcaseMedical,
  TbHome,
  TbReportMedical,
  TbLogout,
  TbMessageCircle,
  TbChevronLeft,
  TbChevronRight,
  TbStethoscope,
  TbUserPlus,
  TbClipboardList,
  TbSettings,
  TbCalendarEvent,
  TbClipboardCheck,
} from "react-icons/tb";
import { useAuth } from "@/hooks/useAuth";
import { usePathname } from "next/navigation";
import { ROUTES, NAVIGATION_ITEMS } from "@/routes/routePaths";

const iconMap: Record<string, React.ReactNode> = {
  HomeIcon: <TbHome />,
  ChatBubbleOvalLeftIcon: <TbMessageCircle />,
  ClipboardDocumentListIcon: <TbReportMedical />,
  UserGroupIcon: <TbUserPlus />,
  DocumentChartBarIcon: <TbClipboardList />,
  StethoscopeIcon: <TbStethoscope />,
  ActivityIcon: <TbClipboardList />,
  CalendarIcon: <TbCalendarEvent />,
  ClipboardCheckIcon: <TbClipboardCheck />,
};

export default function Sidebar() {
  const [isExpanded, setIsExpanded] = useState(true);
  const { user, logout, isAuthenticated } = useAuth();
  const pathname = usePathname();

  const initials = useMemo(() => {
    const first = user?.first_name?.[0] || "";
    const last = user?.last_name?.[0] || "";
    return `${first}${last}`.toUpperCase() || "US";
  }, [user]);

  if (!isAuthenticated) return null;

  const isDoctor = user?.tipo === "doctor";
  const isActivePath = (path: string) =>
    pathname === path || Boolean(pathname && pathname.startsWith(`${path}/`));

  const navItemClass = (active: boolean) =>
    `group relative flex min-h-11 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
      active
        ? "bg-white/14 text-white shadow-md before:absolute before:left-0 before:top-2 before:bottom-2 before:w-1 before:rounded-r-full before:bg-white"
        : "nav-muted-text hover:bg-white/10 hover:text-white"
    }`;

  return (
    <aside
      className={`nav-shell h-screen shrink-0 border-r border-white/10 transition-all duration-300 ${
        isExpanded ? "w-60" : "w-[74px]"
      }`}
    >
      <div className="h-full flex flex-col">
        <div className="px-3 py-4 border-b border-white/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="relative w-10 h-10 rounded-xl overflow-hidden shadow">
                <Image src="/assets/img/icon192.png" alt="Medicheck" fill className="object-cover" sizes="40px" />
              </div>
              {isExpanded && <span className="font-bold tracking-tight text-2xl leading-none">medicheck</span>}
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsExpanded((prev) => !prev)}
              className="text-white hover:bg-white/10"
              aria-label="Contraer menú"
            >
              {isExpanded ? <TbChevronLeft className="h-4 w-4" /> : <TbChevronRight className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        <div className="px-3 py-3">
          <Link
            href={ROUTES.PROTECTED.PROFILE}
            className="flex items-center gap-3 rounded-2xl border border-white/15 bg-white/8 p-3 transition hover:bg-white/14"
          >
            <div className="w-9 h-9 rounded-xl bg-white/14 text-white text-sm font-semibold flex items-center justify-center">
              {initials}
            </div>
            {isExpanded && (
              <div className="min-w-0">
                <p className="text-sm font-semibold truncate">{`${user?.first_name || ""} ${user?.last_name || ""}`.trim() || "Usuario"}</p>
                <p className="text-xs nav-muted-text flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-300" />
                  {isDoctor ? "Médico · Activo" : "Paciente · Activo"}
                </p>
              </div>
            )}
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 pb-2">
          {isExpanded && (
            <div className="mx-2 mb-3 rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/10">
                  <TbBriefcaseMedical className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-white/55">
                    {isDoctor ? "Flujo médico" : "Área de paciente"}
                  </p>
                  <p className="mt-1 text-sm font-medium text-white">
                    {isDoctor ? "Panel profesional" : "Panel personal"}
                  </p>
                  <p className="mt-1 text-xs nav-muted-text">
                    {isDoctor ? "Prioriza revisión, pacientes y citas." : "Accede rápido a chat, datos y seguimiento."}
                  </p>
                </div>
              </div>
            </div>
          )}
          <div className="space-y-1">
            {(isDoctor ? NAVIGATION_ITEMS.doctor : NAVIGATION_ITEMS.main).map((item) => (
              <Link key={item.path} href={item.path} className={navItemClass(isActivePath(item.path))}>
                <span className="text-lg">{iconMap[item.icon] || <TbHome />}</span>
                {isExpanded && <span>{item.name === "Chat" ? "Chat · Hipo" : item.name}</span>}
              </Link>
            ))}
          </div>
        </nav>

        <div className="px-2 py-3 border-t border-white/10 space-y-1">
          <Link href={ROUTES.PROTECTED.PROFILE} className={navItemClass(isActivePath(ROUTES.PROTECTED.PROFILE))}>
            <span className="text-lg">
              <TbSettings />
            </span>
            {isExpanded && <span>Perfil y ajustes</span>}
          </Link>
          <button
            type="button"
            onClick={logout}
            className="group relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-white/90 hover:bg-red-500/15 hover:text-red-100 transition"
          >
            <span className="text-lg">
              <TbLogout />
            </span>
            {isExpanded && <span>Cerrar sesión</span>}
          </button>
        </div>
      </div>
    </aside>
  );
}
