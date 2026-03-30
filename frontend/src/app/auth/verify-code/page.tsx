"use client"

import React, { useState, useRef, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import API from '@/services/api';
import { useApiError } from '@/hooks/useApiError';
import { ROUTES } from '@/routes/routePaths';

const PASSWORD_RESET_EMAIL_KEY = 'password_reset_email';

export default function VerifyCode() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailFromQuery = searchParams.get('email');
  const [email, setEmail] = useState<string | null>(emailFromQuery);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [verificationMessage, setVerificationMessage] = useState('');
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
    const storedEmail = typeof window !== 'undefined'
      ? window.sessionStorage.getItem(PASSWORD_RESET_EMAIL_KEY)
      : null;
    const resolvedEmail = emailFromQuery || storedEmail;

    if (resolvedEmail) {
      setEmail(resolvedEmail);
      if (typeof window !== 'undefined') {
        window.sessionStorage.setItem(PASSWORD_RESET_EMAIL_KEY, resolvedEmail);
      }
    }

    if (inputRefs[0].current) {
      inputRefs[0].current.focus();
    }
  }, [emailFromQuery]);

  const handleCodeChange = (index: number, value: string) => {
    if (value && !/^\d*$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);

    if (value && index < inputRefs.length - 1 && inputRefs[index + 1].current) {
      inputRefs[index + 1].current?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (!code[index] && index > 0 && inputRefs[index - 1].current) {
        inputRefs[index - 1].current?.focus();
      }
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text');

    if (/^\d+$/.test(pastedData)) {
      const digits = pastedData.split('').slice(0, 6);
      const newCode = [...code];

      digits.forEach((digit, index) => {
        if (index < newCode.length) {
          newCode[index] = digit;
        }
      });

      setCode(newCode);

      const lastFilledIndex = Math.min(digits.length - 1, inputRefs.length - 1);
      if (inputRefs[lastFilledIndex].current) {
        inputRefs[lastFilledIndex].current?.focus();
      }
    }
  };

  const verifyCode = async () => {
    const fullCode = code.join('');

    if (fullCode.length !== 6) {
      setVerificationMessage('Por favor, ingresa el código completo de 6 dígitos.');
      return;
    }

    if (!email) {
      setVerificationMessage('No se pudo determinar el correo electrónico.');
      return;
    }

    setIsSubmitting(true);
    clearError();

    try {
      await API.post('password/reset/verify/', {
        email,
        code: fullCode,
      });

      if (typeof window !== 'undefined' && email) {
        window.sessionStorage.setItem(PASSWORD_RESET_EMAIL_KEY, email);
      }

      router.push(
        `${ROUTES.PUBLIC.RECOVER_PASSWORD}?verified=true&email=${encodeURIComponent(email)}&code=${encodeURIComponent(fullCode)}`
      );
    } catch (err) {
      handleApiError(err);
      setVerificationMessage('No se pudo continuar con el restablecimiento.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendCode = async () => {
    if (!email) return;

    setIsSubmitting(true);
    clearError();

    try {
      await API.post('password/reset/request/', { email });
      setVerificationMessage('Se ha enviado un nuevo código a tu correo electrónico.');
    } catch (err) {
      handleApiError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="w-full max-w-sm mx-auto mt-10 shadow-md">
      <CardContent className="p-6">
        <div className="text-center mb-6">
          <h2 className="text-xl font-semibold">Ingresar el código</h2>
          <p className="text-gray-500 mt-1 text-sm">
            Enviamos el código a
            <br />
            <span className="font-medium">{email || 'tu correo electrónico'}</span>
          </p>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
        )}

        {verificationMessage && (
          <p className="text-center text-sm mb-4 text-orange-500">{verificationMessage}</p>
        )}

        <div className="flex justify-center space-x-3 mb-6">
          {[0, 1, 2, 3, 4, 5].map((index) => (
            <input
              key={index}
              ref={inputRefs[index]}
              type="text"
              maxLength={1}
              value={code[index]}
              onChange={(e) => handleCodeChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              onPaste={index === 0 ? handlePaste : undefined}
              className="w-10 h-12 text-center font-bold text-xl border rounded-md focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none"
            />
          ))}
        </div>

        <Button 
          onClick={verifyCode} 
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-md" 
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Verificando...' : 'Verificar código'}
        </Button>

        <div className="text-center mt-4">
          <button 
            onClick={handleResendCode} 
            className="text-blue-600 text-sm font-medium hover:underline"
            disabled={isSubmitting}
          >
            Reenviar código
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
