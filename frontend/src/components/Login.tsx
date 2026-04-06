"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { GoogleOAuthProvider, GoogleLogin, CredentialResponse } from "@react-oauth/google";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { TbLock, TbUser, TbLoader, TbAlertTriangle, TbLogin, TbBrandGoogle } from "react-icons/tb";
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

export default function Login() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fromRoute = searchParams.get("from");
  const safeFromRoute = isSafeInternalPath(fromRoute) ? fromRoute : null;
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  const { login, loginWithGoogle, error: authError, loading } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormInputs>({
    resolver: zodResolver(loginSchema),
  });

  const [googleError, setGoogleError] = useState<string | null>(null);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    syncAuthState();
  }, []);

  const redirectAfterAuth = (profile: UserProfile | null) => {
    if (!profile || redirecting) return;
    setRedirecting(true);

    if (!profile.is_profile_completed) {
      router.push(ROUTES.PUBLIC.PROFILE_COMPLETE);
      return;
    }

    if (safeFromRoute && safeFromRoute !== ROUTES.PUBLIC.LOGIN && safeFromRoute !== ROUTES.PUBLIC.HOME) {
      router.push(safeFromRoute);
      return;
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
    } finally {
      setGoogleLoading(false);
    }
  };

  const googleUnavailable = useMemo(
    () => !googleClientId || googleClientId.trim().length === 0,
    [googleClientId]
  );

  return (
    <Card className="w-full max-w-[28rem] rounded-[2rem] border-border/80 bg-card/95 p-4 shadow-xl shadow-primary/10 sm:p-7">
      <CardHeader className="space-y-4 pb-2">
        <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-[1.75rem] border border-primary/15 bg-primary/10">
          <Image src="/assets/img/logo.png" alt="Logo" width={72} height={72} className="rounded-xl" />
        </div>
        <div className="space-y-2 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Acceso a la plataforma</p>
          <CardTitle className="text-3xl tracking-tight">Iniciar sesion</CardTitle>
          <p className="text-sm leading-7 text-muted-foreground">
            Entra a MediCheck para continuar con tu seguimiento, revisar tu historial o acceder al panel profesional.
          </p>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        {(authError || googleError) && (
          <Alert variant="destructive" className="mb-4 rounded-2xl">
            <AlertDescription className="flex items-center gap-2">
              <TbAlertTriangle className="h-5 w-5" />
              <span>{authError || googleError}</span>
            </AlertDescription>
          </Alert>
        )}

        <div className="mb-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Acceso rapido</p>
          {googleUnavailable ? (
            <Button type="button" className="w-full rounded-full" variant="secondary" disabled>
              <TbBrandGoogle className="h-5 w-5" />
              Google no disponible
            </Button>
          ) : (
            <GoogleOAuthProvider clientId={googleClientId}>
              <div className="rounded-[1.4rem] border border-border/80 bg-card px-4 py-3 shadow-sm transition hover:border-primary/25">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                      <TbBrandGoogle className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold leading-none text-foreground">Continuar con Google</p>
                      <p className="mt-1 text-sm text-muted-foreground">Acceso rápido sin contraseña</p>
                    </div>
                  </div>
                  <div className="text-muted-foreground">›</div>
                </div>
                <div className="mt-3 flex justify-center overflow-hidden rounded-xl border border-border/60 bg-background/80 px-2 py-2">
                  <GoogleLogin
                    onSuccess={handleGoogleSuccess}
                    onError={() => setGoogleError("Error al iniciar sesión con Google. Intenta nuevamente.")}
                    useOneTap={false}
                    auto_select={false}
                    theme="outline"
                    text="signin_with"
                    shape="rectangular"
                    size="large"
                    locale="es"
                    ux_mode="popup"
                  />
                </div>
              </div>
              {googleLoading && (
                <p className="text-center text-sm text-muted-foreground mt-2">Validando sesión con Google...</p>
              )}
            </GoogleOAuthProvider>
          )}
        </div>

        <div className="my-5 flex items-center gap-4">
          <Separator className="flex-1" />
          <span className="text-sm text-muted-foreground">o con tu cuenta</span>
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
              <p className="text-red-500 text-sm mt-1">{errors.username_or_email.message}</p>
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
            {errors.password && <p className="text-red-500 text-sm mt-1">{errors.password.message}</p>}
          </div>
          <Button type="submit" disabled={loading || googleLoading} className="w-full min-h-12 rounded-2xl text-base">
            {loading ? (
              <span className="flex items-center justify-center">
                <TbLoader className="animate-spin h-5 w-5 mr-2" />
                Cargando...
              </span>
            ) : (
              <span className="flex items-center justify-center">
                <TbLogin className="h-5 w-5 mr-2" />
                Ingresar
              </span>
            )}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="pt-2 text-center">
        <p className="w-full">
          ¿No tienes cuenta?
          <Link href={ROUTES.PUBLIC.PROFILE_TYPE} className="ml-2 font-medium text-primary hover:underline">
            Regístrate
          </Link>
        </p>
      </CardFooter>
    </Card>
  );
}
