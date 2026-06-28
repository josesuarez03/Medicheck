"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRouter, useSearchParams } from "next/navigation";
import API from "@/services/api";
import { useApiError } from "@/hooks/useApiError";
import {
  TbAlertTriangle,
  TbArrowLeft,
  TbCheck,
  TbKey,
  TbLoader,
  TbLock,
  TbMail,
  TbShieldLock,
} from "react-icons/tb";
import { ROUTES } from "@/routes/routePaths";

const PASSWORD_RESET_EMAIL_KEY = "password_reset_email";

const requestResetSchema = z.object({
  email: z.string().min(1, { message: "El email es obligatorio" }).email({ message: "Email inválido" }),
});

const resetPasswordSchema = z
  .object({
    code: z.string().min(1, { message: "El código de verificación es obligatorio" }),
    password: z
      .string()
      .min(8, { message: "La contraseña debe tener al menos 8 caracteres" })
      .regex(/[A-Z]/, { message: "Debe contener al menos una letra mayúscula" })
      .regex(/[a-z]/, { message: "Debe contener al menos una letra minúscula" })
      .regex(/[0-9]/, { message: "Debe contener al menos un número" })
      .regex(/[@$!%*?&]/, { message: "Debe contener al menos un carácter especial (@$!%*?&)" }),
    confirmPassword: z.string().min(1, { message: "La confirmación de contraseña es obligatoria" }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

type RequestResetInputs = z.infer<typeof requestResetSchema>;
type ResetPasswordInputs = z.infer<typeof resetPasswordSchema>;

export default function RecoverPassword() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const emailFromQuery = searchParams.get("email");
  const codeFromQuery = searchParams.get("code");
  const verified = searchParams.get("verified");

  const [recoveryEmail, setRecoveryEmail] = useState<string | null>(emailFromQuery);
  const [mode, setMode] = useState<"request" | "reset">(verified === "true" ? "reset" : "request");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const { error, handleApiError, clearError } = useApiError();

  const requestForm = useForm<RequestResetInputs>({
    resolver: zodResolver(requestResetSchema),
    defaultValues: {
      email: emailFromQuery || "",
    },
  });

  const resetForm = useForm<ResetPasswordInputs>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      code: codeFromQuery || "",
    },
  });

  useEffect(() => {
    const storedEmail = typeof window !== "undefined" ? window.sessionStorage.getItem(PASSWORD_RESET_EMAIL_KEY) : null;
    const resolvedEmail = emailFromQuery || storedEmail;

    if (resolvedEmail) {
      setRecoveryEmail(resolvedEmail);
      requestForm.setValue("email", resolvedEmail);
    }

    if (resolvedEmail && codeFromQuery && verified === "true") {
      setMode("reset");
      resetForm.setValue("code", codeFromQuery);
    }
  }, [emailFromQuery, codeFromQuery, verified, requestForm, resetForm]);

  const onRequestSubmit = async (data: RequestResetInputs) => {
    setIsSubmitting(true);
    clearError();
    setSuccessMessage(null);

    try {
      await API.post("password/reset/request/", { email: data.email });

      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(PASSWORD_RESET_EMAIL_KEY, data.email);
      }

      setRecoveryEmail(data.email);
      router.push(`${ROUTES.PUBLIC.VERIFY_CODE}?email=${data.email}`);
    } catch (err) {
      handleApiError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const onResetSubmit = async (data: ResetPasswordInputs) => {
    if (!recoveryEmail || !data.code) {
      handleApiError(new Error("Información de verificación inválida o expirada"));
      return;
    }

    setIsSubmitting(true);
    clearError();
    setSuccessMessage(null);

    try {
      await API.post("password/reset/verify/", {
        email: recoveryEmail,
        code: data.code,
        new_password: data.password,
        confirm_password: data.confirmPassword,
      });

      setSuccessMessage("Contraseña restablecida con éxito");
      if (typeof window !== "undefined") {
        window.sessionStorage.removeItem(PASSWORD_RESET_EMAIL_KEY);
      }

      setTimeout(() => {
        router.push(ROUTES.PUBLIC.LOGIN);
      }, 2000);
    } catch (err) {
      handleApiError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="w-full max-w-[30rem] rounded-[2rem] border-border/80 bg-card/95 p-4 shadow-xl shadow-primary/10 sm:p-7">
      <CardHeader className="space-y-3 pb-2 text-center">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-[1.5rem] border border-primary/15 bg-primary/10 text-primary">
          {mode === "request" ? <TbKey className="h-9 w-9" /> : <TbShieldLock className="h-9 w-9" />}
        </div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Acceso seguro</p>
        <CardTitle className="text-3xl tracking-tight">
          {mode === "request" ? "Recuperar contraseña" : "Restablecer contraseña"}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-2">
        {successMessage && (
          <Alert
            variant="default"
            className="mb-4 rounded-2xl border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-100"
          >
            <AlertDescription className="flex items-center">
              <TbCheck className="mr-2 h-5 w-5" />
              {successMessage}
            </AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive" className="mb-4 rounded-2xl">
            <AlertDescription className="flex items-center">
              <TbAlertTriangle className="mr-2 h-5 w-5" />
              {error.message}
            </AlertDescription>
          </Alert>
        )}

        {mode === "request" ? (
          <form onSubmit={requestForm.handleSubmit(onRequestSubmit)} className="space-y-4">
            <div>
              <Label htmlFor="email" className="mb-2 flex items-center">
                <TbMail className="mr-2 h-5 w-5 text-primary" />
                Email
              </Label>
              <Input
                id="email"
                type="email"
                {...requestForm.register("email")}
                className={`min-h-12 rounded-2xl bg-background ${
                  requestForm.formState.errors.email ? "border-red-500" : ""
                }`}
              />
              {requestForm.formState.errors.email && (
                <p className="mt-1 text-sm text-red-500">{requestForm.formState.errors.email.message}</p>
              )}
            </div>

            <Button type="submit" className="min-h-12 w-full rounded-2xl" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <TbLoader className="mr-2 h-5 w-5 animate-spin" />
                  <span>Enviando...</span>
                </>
              ) : (
                <>
                  <TbMail className="mr-2 h-5 w-5" />
                  <span>Enviar código de recuperación</span>
                </>
              )}
            </Button>

            <p className="mt-4 text-center text-sm">
              <Link href={ROUTES.PUBLIC.LOGIN} className="inline-flex items-center justify-center text-primary hover:underline">
                <TbArrowLeft className="mr-1 h-4 w-4" />
                <span>Volver al login</span>
              </Link>
            </p>
          </form>
        ) : (
          <form onSubmit={resetForm.handleSubmit(onResetSubmit)} className="space-y-4">
            <input type="hidden" {...resetForm.register("code")} />

            <div>
              <Label htmlFor="recovery-email" className="mb-2 flex items-center">
                <TbMail className="mr-2 h-5 w-5 text-primary" />
                Correo de recuperación
              </Label>
              <Input
                id="recovery-email"
                type="email"
                value={recoveryEmail || ""}
                disabled
                className="min-h-12 rounded-2xl bg-muted/50"
              />
            </div>

            <div>
              <Label htmlFor="password" className="mb-2 flex items-center">
                <TbLock className="mr-2 h-5 w-5 text-primary" />
                Nueva contraseña
              </Label>
              <Input
                id="password"
                type="password"
                {...resetForm.register("password")}
                className={`min-h-12 rounded-2xl bg-background ${
                  resetForm.formState.errors.password ? "border-red-500" : ""
                }`}
              />
              {resetForm.formState.errors.password && (
                <p className="mt-1 text-sm text-red-500">{resetForm.formState.errors.password.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="confirmPassword" className="mb-2 flex items-center">
                <TbShieldLock className="mr-2 h-5 w-5 text-primary" />
                Confirmar contraseña
              </Label>
              <Input
                id="confirmPassword"
                type="password"
                {...resetForm.register("confirmPassword")}
                className={`min-h-12 rounded-2xl bg-background ${
                  resetForm.formState.errors.confirmPassword ? "border-red-500" : ""
                }`}
              />
              {resetForm.formState.errors.confirmPassword && (
                <p className="mt-1 text-sm text-red-500">{resetForm.formState.errors.confirmPassword.message}</p>
              )}
            </div>

            <Button type="submit" className="min-h-12 w-full rounded-2xl" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <TbLoader className="mr-2 h-5 w-5 animate-spin" />
                  <span>Restableciendo...</span>
                </>
              ) : (
                <>
                  <TbCheck className="mr-2 h-5 w-5" />
                  <span>Restablecer contraseña</span>
                </>
              )}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
