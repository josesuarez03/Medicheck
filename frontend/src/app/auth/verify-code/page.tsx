"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { TbAlertTriangle, TbMailCheck } from "react-icons/tb";
import API from "@/services/api";
import { useApiError } from "@/hooks/useApiError";
import { ROUTES } from "@/routes/routePaths";

const PASSWORD_RESET_EMAIL_KEY = "password_reset_email";

export default function VerifyCode() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailFromQuery = searchParams.get("email");

  const [email, setEmail] = useState<string | null>(emailFromQuery);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [verificationMessage, setVerificationMessage] = useState("");
  const { error, handleApiError, clearError } = useApiError();

  const inputRefs = [
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
  ];

  useEffect(() => {
    const storedEmail = typeof window !== "undefined" ? window.sessionStorage.getItem(PASSWORD_RESET_EMAIL_KEY) : null;
    const resolvedEmail = emailFromQuery || storedEmail;

    if (resolvedEmail) {
      setEmail(resolvedEmail);
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(PASSWORD_RESET_EMAIL_KEY, resolvedEmail);
      }
    }

    inputRefs[0].current?.focus();
  }, [emailFromQuery]);

  const handleCodeChange = (index: number, value: string) => {
    if (value && !/^\d*$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);

    if (value && index < inputRefs.length - 1) {
      inputRefs[index + 1].current?.focus();
    }
  };

  const handleKeyDown = (index: number, event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Backspace" && !code[index] && index > 0) {
      inputRefs[index - 1].current?.focus();
    }
  };

  const handlePaste = (event: React.ClipboardEvent) => {
    event.preventDefault();
    const pastedData = event.clipboardData.getData("text");

    if (/^\d+$/.test(pastedData)) {
      const digits = pastedData.split("").slice(0, 6);
      const newCode = [...code];

      digits.forEach((digit, index) => {
        if (index < newCode.length) newCode[index] = digit;
      });

      setCode(newCode);
      inputRefs[Math.min(digits.length - 1, inputRefs.length - 1)].current?.focus();
    }
  };

  const verifyCode = async () => {
    const fullCode = code.join("");

    if (fullCode.length !== 6) {
      setVerificationMessage("Por favor, ingresa el código completo de 6 dígitos.");
      return;
    }

    if (!email) {
      setVerificationMessage("No se pudo determinar el correo electrónico.");
      return;
    }

    setIsSubmitting(true);
    clearError();

    try {
      await API.post("password/reset/verify/", {
        email,
        code: fullCode,
      });

      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(PASSWORD_RESET_EMAIL_KEY, email);
      }

      router.push(
        `${ROUTES.PUBLIC.RECOVER_PASSWORD}?verified=true&email=${encodeURIComponent(email)}&code=${encodeURIComponent(fullCode)}`
      );
    } catch (err) {
      handleApiError(err);
      setVerificationMessage("No se pudo continuar con el restablecimiento.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendCode = async () => {
    if (!email) return;

    setIsSubmitting(true);
    clearError();

    try {
      await API.post("password/reset/request/", { email });
      setVerificationMessage("Se ha enviado un nuevo código a tu correo electrónico.");
    } catch (err) {
      handleApiError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="w-full max-w-[28rem] rounded-[2rem] border-border/80 bg-card/95 p-4 shadow-xl shadow-primary/10 sm:p-7">
      <CardHeader className="space-y-3 pb-2 text-center">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-[1.5rem] border border-primary/15 bg-primary/10 text-primary">
          <TbMailCheck className="h-9 w-9" />
        </div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Verificación</p>
        <CardTitle className="text-3xl tracking-tight">Ingresar el código</CardTitle>
        <p className="text-sm leading-7 text-muted-foreground">
          Enviamos el código a
          <br />
          <span className="font-medium text-foreground">{email || "tu correo electrónico"}</span>
        </p>
      </CardHeader>
      <CardContent className="p-0 pt-2">
        {error && (
          <Alert variant="destructive" className="mb-4 rounded-2xl">
            <AlertDescription className="flex items-center gap-2">
              <TbAlertTriangle className="h-5 w-5" />
              {error.message}
            </AlertDescription>
          </Alert>
        )}

        {verificationMessage && <p className="mb-4 text-center text-sm text-primary">{verificationMessage}</p>}

        <div className="mb-6 flex justify-center space-x-3">
          {[0, 1, 2, 3, 4, 5].map((index) => (
            <input
              key={index}
              ref={inputRefs[index]}
              type="text"
              maxLength={1}
              value={code[index]}
              onChange={(event) => handleCodeChange(index, event.target.value)}
              onKeyDown={(event) => handleKeyDown(index, event)}
              onPaste={index === 0 ? handlePaste : undefined}
              className="h-14 w-11 rounded-2xl border border-input bg-background text-center text-xl font-bold outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
            />
          ))}
        </div>

        <Button onClick={verifyCode} className="min-h-12 w-full rounded-2xl" disabled={isSubmitting}>
          {isSubmitting ? "Verificando..." : "Verificar código"}
        </Button>

        <div className="mt-4 text-center">
          <button onClick={handleResendCode} className="text-sm font-medium text-primary hover:underline" disabled={isSubmitting}>
            Reenviar código
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
