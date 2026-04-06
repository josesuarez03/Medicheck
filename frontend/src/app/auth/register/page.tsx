"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
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
import { register as apiRegister } from "@/services/api";
import axios from "axios";
import {
  TbBrandGoogle,
  TbLock,
  TbMail,
  TbUser,
  TbUsers,
  TbLoader,
  TbAlertTriangle,
  TbLogin,
  TbUserCircle,
  TbCheckbox,
  TbAt,
} from "react-icons/tb";
import { ROUTES } from "@/routes/routePaths";
import { UserProfile } from "@/types/user";

const registerSchema = z
  .object({
    email: z.string().min(1, { message: "El email es obligatorio" }).email({ message: "Email inválido" }),
    username: z
      .string()
      .min(3, { message: "El nombre de usuario debe tener al menos 3 caracteres" })
      .max(30, { message: "El nombre de usuario no puede exceder los 30 caracteres" })
      .regex(/^[a-zA-Z0-9_]+$/, {
        message: "El nombre de usuario solo puede contener letras, números y guiones bajos",
      }),
    password: z
      .string()
      .min(8, { message: "La contraseña debe tener al menos 8 caracteres" })
      .regex(/[A-Z]/, { message: "Debe contener al menos una letra mayúscula" })
      .regex(/[a-z]/, { message: "Debe contener al menos una letra minúscula" })
      .regex(/[0-9]/, { message: "Debe contener al menos un número" })
      .regex(/[@$!%*?&]/, { message: "Debe contener al menos un carácter especial (@$!%*?&)" }),
    confirmPassword: z.string().min(1, { message: "La confirmación de contraseña es obligatoria" }),
    first_name: z
      .string()
      .min(1, { message: "El nombre es obligatorio" })
      .regex(/^[a-zA-Z\s]+$/, { message: "El nombre solo puede contener letras y espacios" })
      .max(50, { message: "El nombre no puede exceder los 50 caracteres" }),
    last_name: z
      .string()
      .min(1, { message: "El apellido es obligatorio" })
      .regex(/^[a-zA-Z\s]+$/, { message: "El apellido solo puede contener letras y espacios" })
      .max(50, { message: "El apellido no puede exceder los 50 caracteres" }),
    tipo: z.string().min(1, { message: "El tipo de usuario es obligatorio" }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

type RegisterFormInputs = z.infer<typeof registerSchema>;

export default function Register() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const type = searchParams.get("type");
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  const { loginWithGoogle, error: authError, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [googleError, setGoogleError] = useState<string | null>(null);
  const [googleLoading, setGoogleLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
  } = useForm<RegisterFormInputs>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      tipo: type || "patient",
    },
  });

  useEffect(() => {
    if (!type) {
      router.push(ROUTES.PUBLIC.PROFILE_TYPE);
    } else {
      localStorage.setItem("selectedProfileType", type);
      setValue("tipo", type);
    }
  }, [type, router, setValue]);

  const redirectAfterAuth = (profile: UserProfile | null) => {
    if (!profile) return;
    if (!profile.is_profile_completed) {
      router.push(ROUTES.PUBLIC.PROFILE_COMPLETE);
      return;
    }
    router.push(ROUTES.PROTECTED.DASHBOARD);
  };

  const onSubmit = async (data: RegisterFormInputs) => {
    setLoading(true);
    setError(null);

    const registerData = {
      email: data.email,
      username: data.username,
      password: data.password,
      password2: data.confirmPassword,
      first_name: data.first_name,
      last_name: data.last_name,
      tipo: data.tipo,
    };

    try {
      await apiRegister(registerData);
      router.push(ROUTES.PUBLIC.LOGIN);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        if (!err.response) {
          setError("No se puede conectar al servidor. Verifica tu conexión.");
        } else {
          const errorData = err.response.data;
          let errorMessage = "Error en el registro. Revisa tus datos.";
          if (typeof errorData === "object" && errorData !== null) {
            errorMessage =
              errorData.detail ||
              errorData.email?.[0] ||
              errorData.username?.[0] ||
              errorData.non_field_errors?.[0] ||
              errorMessage;
          }
          setError(errorMessage);
        }
      } else {
        setError("Error desconocido. Inténtalo nuevamente.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential || googleLoading) {
      setGoogleError("No se pudo obtener credenciales de Google.");
      return;
    }

    try {
      setGoogleLoading(true);
      setGoogleError(null);
      const profileType = localStorage.getItem("selectedProfileType") || "patient";
      const profile = await loginWithGoogle(credentialResponse.credential, profileType);
      redirectAfterAuth(profile);
    } finally {
      setGoogleLoading(false);
    }
  };

  const getUserTypeText = () => (type === "doctor" ? "Médico" : "Paciente");
  const googleUnavailable = useMemo(() => !googleClientId || googleClientId.trim().length === 0, [googleClientId]);

  return (
    <Card className="w-full max-w-[34rem] rounded-[2rem] border-border/80 bg-card/95 p-4 shadow-xl shadow-primary/10 sm:p-7">
      <CardHeader className="space-y-4 pb-2">
        <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-[1.75rem] border border-primary/15 bg-primary/10">
          <Image src="/assets/img/logo.png" alt="Logo" width={72} height={72} className="rounded-xl" />
        </div>
        <div className="space-y-2 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Nueva cuenta</p>
          <CardTitle className="text-center">
          <div className="flex items-center justify-center text-2xl font-semibold tracking-tight">
            {type === "doctor" ? (
              <TbUserCircle className="w-7 h-7 mr-2 text-primary" />
            ) : (
              <TbUsers className="w-7 h-7 mr-2 text-primary" />
            )}
            Registro como {getUserTypeText()}
          </div>
          </CardTitle>
          <p className="text-sm leading-7 text-muted-foreground">
            Crea tu acceso y luego completaras el perfil para paciente o profesional dentro de la aplicacion.
          </p>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        {(authError || error || googleError) && (
          <Alert variant="destructive" className="mb-4 rounded-2xl">
            <AlertDescription className="flex items-center">
              <TbAlertTriangle className="w-5 h-5 mr-2" />
              <span>{authError || error || googleError}</span>
            </AlertDescription>
          </Alert>
        )}

        <div className="mb-5">
          {googleUnavailable ? (
            <Button type="button" variant="secondary" className="w-full rounded-full" disabled>
              <TbBrandGoogle className="w-5 h-5 mr-2" />
              Google no disponible
            </Button>
          ) : (
            <GoogleOAuthProvider clientId={googleClientId}>
              <GoogleAuthButton
                mode="signup"
                loading={googleLoading}
                onSuccess={handleGoogleSuccess}
                onError={() => setGoogleError("Error al iniciar sesión con Google. Intenta nuevamente.")}
              />
            </GoogleOAuthProvider>
          )}
          {googleLoading && (
            <p className="mt-2 text-center text-sm text-muted-foreground">Validando sesión con Google...</p>
          )}
        </div>

        <Separator className="my-5" />

        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <Label className="mb-2 flex items-center">
              <TbMail className="w-5 h-5 mr-2 text-primary" />
              Email
            </Label>
            <Input type="email" {...register("email")} className="min-h-12 rounded-2xl bg-background" />
            {errors.email && <p className="text-red-500 text-sm">{errors.email.message}</p>}
          </div>
          <div>
            <Label className="mb-2 flex items-center">
              <TbUser className="w-5 h-5 mr-2 text-primary" />
              Nombre
            </Label>
            <Input type="text" {...register("first_name")} className="min-h-12 rounded-2xl bg-background" />
            {errors.first_name && <p className="text-red-500 text-sm">{errors.first_name.message}</p>}
          </div>
          <div>
            <Label className="mb-2 flex items-center">
              <TbUsers className="w-5 h-5 mr-2 text-primary" />
              Apellido
            </Label>
            <Input type="text" {...register("last_name")} className="min-h-12 rounded-2xl bg-background" />
            {errors.last_name && <p className="text-red-500 text-sm">{errors.last_name.message}</p>}
          </div>
          <div className="md:col-span-2">
            <Label className="mb-2 flex items-center">
              <TbAt className="w-5 h-5 mr-2 text-primary" />
              Nombre de usuario
            </Label>
            <Input type="text" {...register("username")} className="min-h-12 rounded-2xl bg-background" />
            {errors.username && <p className="text-red-500 text-sm">{errors.username.message}</p>}
          </div>
          <div>
            <Label className="mb-2 flex items-center">
              <TbLock className="w-5 h-5 mr-2 text-primary" />
              Contraseña
            </Label>
            <Input type="password" {...register("password")} className="min-h-12 rounded-2xl bg-background" />
            {errors.password && <p className="text-red-500 text-sm">{errors.password.message}</p>}
          </div>
          <div>
            <Label className="mb-2 flex items-center">
              <TbCheckbox className="w-5 h-5 mr-2 text-primary" />
              Confirmar Contraseña
            </Label>
            <Input type="password" {...register("confirmPassword")} className="min-h-12 rounded-2xl bg-background" />
            {errors.confirmPassword && <p className="text-red-500 text-sm">{errors.confirmPassword.message}</p>}
          </div>

          <input type="hidden" {...register("tipo")} />

          <div className="md:col-span-2">
          <Button type="submit" className="w-full min-h-12 rounded-2xl text-base" disabled={loading || authLoading || googleLoading}>
            {loading || authLoading ? (
              <>
                <TbLoader className="animate-spin h-5 w-5 mr-2" />
                Cargando...
              </>
            ) : (
              <>
                <TbLogin className="w-5 h-5 mr-2" />
                Registrarse
              </>
            )}
          </Button>
          </div>
        </form>
      </CardContent>
      <CardFooter className="pt-2 text-center">
        <p className="w-full">
          ¿Ya tienes cuenta?
          <Link href={ROUTES.PUBLIC.LOGIN} className="ml-2 font-medium text-primary hover:underline">
            Inicia sesión
          </Link>
        </p>
      </CardFooter>
    </Card>
  );
}
