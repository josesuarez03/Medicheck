"use client";

import Link from "next/link";
import { TbArrowRight } from "react-icons/tb";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { TriageTone } from "@/types/clinic";

export function triageToneClass(level: TriageTone | string) {
  const value = String(level).toLowerCase();
  if (value.includes("urg")) return "border-red-300 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100";
  if (value.includes("mod")) return "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100";
  return "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100";
}

export function TriagePill({ level }: { level: TriageTone | string }) {
  return (
    <span className={cn("inline-flex min-h-9 items-center rounded-full border px-3 py-1 text-xs font-semibold capitalize", triageToneClass(level))}>
      {level}
    </span>
  );
}

export function MetricCard({
  label,
  value,
  supporting,
}: {
  label: string;
  value: string | number;
  supporting: string;
}) {
  return (
    <Card className="metric-card">
      <CardContent className="p-0">
        <p className="metric-label">{label}</p>
        <p className="metric-value">{value}</p>
        <p className="mt-2 text-sm text-muted-foreground">{supporting}</p>
      </CardContent>
    </Card>
  );
}

export function PageHero({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: React.ReactNode;
}) {
  return (
    <section className="hero-panel subtle-grid overflow-hidden p-6 md:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">{eyebrow}</p>
      <h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-foreground md:text-5xl">{title}</h2>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-muted-foreground md:text-base md:leading-8">{description}</p>
      {actions && <div className="mt-6 flex flex-wrap gap-3">{actions}</div>}
    </section>
  );
}

export function InfoPanel({
  title,
  description,
  actionHref,
  actionLabel,
}: {
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <Card className="clinical-shell">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      {actionHref && actionLabel ? (
        <CardContent className="pt-0">
          <Button asChild variant="outline" className="rounded-full">
            <Link href={actionHref}>
              {actionLabel}
              <TbArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      ) : null}
    </Card>
  );
}
