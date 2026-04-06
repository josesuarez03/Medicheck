"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { GoogleOAuthProvider, CredentialResponse } from "@react-oauth/google";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import GoogleAuthButton from "@/components/auth/GoogleAuthButton";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { TbLock, TbUser, TbLoader, TbAlertTriangle, TbLogin } from "react-icons/tb";
import { ROUTES } from "@/routes/routePaths";
import { syncAuthState } from "@/utils/authSync";
import { UserProfile } from "@/types/user";

const loginSchema = z.object({
  username_or_email: z.string().min(1, { message: "El usuario o email es obligatorio" }),
  password: z.string().min(1, { message: "La contraseña es obligatoria" }),
});

type LoginFormInputs = z.infer<typeof loginSchema>;

const isSafeInternalPath = (path: string | null): path is string => {
  if (!path) return false;
  return path.startsWith("/") && !path.startsWith("//");
};

/* ── Componente interior (necesita estar dentro del Provider) ─────────── */
function LoginInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fromRoute = searchParams.get("from");
  const safeFromRoute = isSafeInternalPath(fromRoute) ? fromRoute : null;

  const { login, loginWithGoogle, error: authError, loading } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormInputs>({ resolver: zodResolver(loginSchema) });

  const [googleError, setGoogleError] = useState<string | null>(null);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => { syncAuthState(); }, []);

  const redirectAfterAuth = (profile: UserProfile | null) => {
    if (!profile || redirecting) return;
    setRedirecting(true);
    if (!profile.is_profile_completed) { router.push(ROUTES.PUBLIC.PROFILE_COMPLETE); return; }
    if (safeFromRoute && safeFromRoute !== ROUTES.PUBLIC.LOGIN && safeFromRoute !== ROUTES.PUBLIC.HOME) {
      router.push(safeFromRoute); return;
    }
    router.push(ROUTES.PROTECTED.DASHBOARD);
  };

  const onSubmit = async (data: LoginFormInputs) => {
    const profile = await login(data.username_or_email, data.password);
    syncAuthState();
    redirectAfterAuth(profile);
  };

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential || googleLoading) {
      setGoogleError("No se pudo obtener una credencial válida de Google.");
      return;
    }
    try {
      setGoogleLoading(true);
      setGoogleError(null);
      const profileType = localStorage.getItem("selectedProfileType") || "patient";
      const profile = await loginWithGoogle(credentialResponse.credential, profileType);
      syncAuthState();
      redirectAfterAuth(profile);
    } catch {
      setGoogleError("Error al iniciar sesión con Google. Inténtalo de nuevo.");
    } finally {
      setGoogleLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-[28rem] rounded-[2rem] border-border/80 bg-card/95 p-4 shadow-xl shadow-primary/10 sm:p-7">
      <CardHeader className="space-y-4 pb-2">
        <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-[1.75rem] border border-primary/15 bg-primary/10">
          <Image src="/assets/img/logo.png" alt="Logo" width={72} height={72} className="rounded-xl" />
        </div>
        <div className="space-y-2 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Acceso a la plataforma</p>
          <CardTitle className="text-3xl tracking-tight">Iniciar sesión</CardTitle>
        </div>
      </CardHeader>

      <CardContent className="pt-2">
        {(authError || googleError) && (
          <Alert variant="destructive" className="mb-4 rounded-2xl">
            <AlertDescription className="flex items-center gap-2">
              <TbAlertTriangle className="h-5 w-5 shrink-0" />
              <span>{authError || googleError}</span>
            </AlertDescription>
          </Alert>
        )}

        {/* ── Botón Google custom ── */}
        <div className="mb-5">
          <GoogleAuthButton
            onSuccess={handleGoogleSuccess}
            onError={() => setGoogleError("Error al iniciar sesión con Google. Inténtalo de nuevo.")}
            loading={googleLoading}
          />
        </div>

        <div className="my-5 flex items-center gap-4">
          <Separator className="flex-1" />
          <span className="text-xs text-muted-foreground">o con tu cuenta</span>
          <Separator className="flex-1" />
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label className="mb-2 flex items-center gap-2 text-sm font-medium">
              <TbUser className="h-5 w-5 text-primary" />
              Usuario o Email
            </Label>
            <Input type="text" {...register("username_or_email")} className="min-h-12 rounded-2xl bg-background" />
            {errors.username_or_email && (
              <p className="mt-1 text-sm text-destructive">{errors.username_or_email.message}</p>
            )}
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <Label className="flex items-center gap-2 text-sm font-medium">
                <TbLock className="h-5 w-5 text-primary" />
                Contraseña
              </Label>
              <Link
                href={`${ROUTES.PUBLIC.RECOVER_PASSWORD}?fromLogin=true`}
                className="text-xs font-medium text-primary hover:underline"
              >
                ¿Olvidaste tu contraseña?
              </Link>
            </div>
            <Input type="password" {...register("password")} className="min-h-12 rounded-2xl bg-background" />
            {errors.password && (
              <p className="mt-1 text-sm text-destructive">{errors.password.message}</p>
            )}
          </div>

          <Button
            type="submit"
            disabled={loading || googleLoading}
            className="w-full min-h-12 rounded-2xl text-base"
          >
            {loading ? (
              <>
                <TbLoader className="mr-2 h-5 w-5 animate-spin" />
                Cargando…
              </>
            ) : (
              <>
                <TbLogin className="mr-2 h-5 w-5" />
                Ingresar
              </>
            )}
          </Button>
        </form>
      </CardContent>

      <CardFooter className="pt-2 text-center">
        <p className="w-full text-sm">
          ¿No tienes cuenta?{" "}
          <Link href={ROUTES.PUBLIC.PROFILE_TYPE} className="font-medium text-primary hover:underline">
            Regístrate
          </Link>
        </p>
      </CardFooter>
    </Card>
  );
}

/* ── Export principal con el Provider envolviendo todo ────────────────── */
export default function Login() {
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  const googleUnavailable = useMemo(
    () => !googleClientId || googleClientId.trim().length === 0,
    [googleClientId]
  );

  if (googleUnavailable) {
    return <LoginInner />;
  }

  return (
    <GoogleOAuthProvider clientId={googleClientId!}>
      <LoginInner />
    </GoogleOAuthProvider>
  );
}
