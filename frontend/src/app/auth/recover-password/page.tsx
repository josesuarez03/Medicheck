"use client"

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useRouter, useSearchParams } from 'next/navigation'; // Cambiado de next/router a next/navigation
import API from '@/services/api';
import { useApiError } from '@/hooks/useApiError';
// Importar los iconos de Tabler
import { 
  TbMail, 
  TbLock, 
  TbShieldLock, 
  TbCheck, 
  TbLoader, 
  TbArrowLeft, 
  TbAlertTriangle,
  TbKey
} from "react-icons/tb";
import { ROUTES } from '@/routes/routePaths';

const PASSWORD_RESET_EMAIL_KEY = 'password_reset_email';

// Esquema para solicitar recuperación (email)
const requestResetSchema = z.object({
  email: z.string()
    .min(1, { message: 'El email es obligatorio' })
    .email({ message: 'Email inválido' }),
});

// Esquema para restablecer la contraseña
const resetPasswordSchema = z.object({
  code: z.string().min(1, { message: 'El código de verificación es obligatorio' }),
  password: z.string()
    .min(8, { message: 'La contraseña debe tener al menos 8 caracteres' })
    .regex(/[A-Z]/, { message: 'Debe contener al menos una letra mayúscula' })
    .regex(/[a-z]/, { message: 'Debe contener al menos una letra minúscula' })
    .regex(/[0-9]/, { message: 'Debe contener al menos un número' })
    .regex(/[@$!%*?&]/, { message: 'Debe contener al menos un carácter especial (@$!%*?&)' }),
  confirmPassword: z.string()
    .min(1, { message: 'La confirmación de contraseña es obligatoria' }),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Las contraseñas no coinciden',
  path: ['confirmPassword'],
});

type RequestResetInputs = z.infer<typeof requestResetSchema>;
type ResetPasswordInputs = z.infer<typeof resetPasswordSchema>;

export default function RecoverPassword() {
  const router = useRouter();
  const searchParams = useSearchParams(); // Usar searchParams en lugar de router.query
  
  // Obtener parámetros de la URL
  const emailFromQuery = searchParams.get('email');
  const codeFromQuery = searchParams.get('code');
  const verified = searchParams.get('verified');
  const [recoveryEmail, setRecoveryEmail] = useState<string | null>(emailFromQuery);
  
  const [mode, setMode] = useState<'request' | 'reset'>(verified === 'true' ? 'reset' : 'request');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const { error, handleApiError, clearError } = useApiError();

  // Formulario para solicitud inicial
  const requestForm = useForm<RequestResetInputs>({
    resolver: zodResolver(requestResetSchema),
    defaultValues: {
      email: emailFromQuery || '',
    },
  });

  // Formulario para restablecer contraseña
  const resetForm = useForm<ResetPasswordInputs>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      code: codeFromQuery || '',
    }
  });

  // Detectar email y código en la URL o en sessionStorage para no pedir el correo otra vez.
  useEffect(() => {
    const storedEmail = typeof window !== 'undefined'
      ? window.sessionStorage.getItem(PASSWORD_RESET_EMAIL_KEY)
      : null;
    const resolvedEmail = emailFromQuery || storedEmail;

    if (resolvedEmail) {
      setRecoveryEmail(resolvedEmail);
      requestForm.setValue('email', resolvedEmail);
    }

    if (resolvedEmail && codeFromQuery && verified === 'true') {
      setMode('reset');
      resetForm.setValue('code', codeFromQuery);
    }
  }, [emailFromQuery, codeFromQuery, verified, requestForm, resetForm]);

  // Manejar solicitud de recuperación
  const onRequestSubmit = async (data: RequestResetInputs) => {
    setIsSubmitting(true);
    clearError();
    setSuccessMessage(null);

    try {
      await API.post('password/reset/request/', {
        email: data.email
      });

      if (typeof window !== 'undefined') {
        window.sessionStorage.setItem(PASSWORD_RESET_EMAIL_KEY, data.email);
      }
      setRecoveryEmail(data.email);

      // En lugar de mostrar un mensaje, redirigir directamente a VerifyCode
      router.push(`${ROUTES.PUBLIC.VERIFY_CODE}?email=${data.email}`);
    } catch (err) {
      handleApiError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Manejar restablecimiento de contraseña
  const onResetSubmit = async (data: ResetPasswordInputs) => {
    if (!recoveryEmail || !data.code) {
      handleApiError(new Error('Información de verificación inválida o expirada'));
      return;
    }

    setIsSubmitting(true);
    clearError();
    setSuccessMessage(null);

    try {
      // Actualizar para usar la ruta correcta de la API y el formato correcto
      await API.post('password/reset/verify/', {
        email: recoveryEmail,
        code: data.code,
        new_password: data.password,
        confirm_password: data.confirmPassword,
      });

      setSuccessMessage('Contraseña restablecida con éxito');
      if (typeof window !== 'undefined') {
        window.sessionStorage.removeItem(PASSWORD_RESET_EMAIL_KEY);
      }
      
      // Redirigir al login después de 2 segundos
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
    <div className="max-w-md mx-auto mt-10 p-6 rounded-lg shadow-md">
      <h1 className="text-2xl font-bold text-center mb-6">
        {mode === 'request' ? (
          <div className="flex items-center justify-center">
            <TbKey className="h-6 w-6 mr-2 text-blue-500" />
            <span>Recuperar Contraseña</span>
          </div>
        ) : (
          <div className="flex items-center justify-center">
            <TbShieldLock className="h-6 w-6 mr-2 text-blue-500" />
            <span>Restablecer Contraseña</span>
          </div>
        )}
      </h1>

      {successMessage && (
        <Alert variant="default" className="mb-4">
          <AlertDescription className="flex items-center">
            <TbCheck className="h-5 w-5 mr-2 text-green-500" />
            {successMessage}
          </AlertDescription>
        </Alert>
      )}
      
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription className="flex items-center">
            <TbAlertTriangle className="h-5 w-5 mr-2" />
            {error.message}
          </AlertDescription>
        </Alert>
      )}

      {mode === 'request' ? (
        // Formulario de solicitud
        <form onSubmit={requestForm.handleSubmit(onRequestSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="email" className="flex items-center">
              <TbMail className="h-5 w-5 mr-2 text-gray-500" />
              Email
            </Label>
            <Input 
              id="email"
              type="email" 
              {...requestForm.register('email')} 
              className={requestForm.formState.errors.email ? 'border-red-500' : ''}
            />
            {requestForm.formState.errors.email && (
              <p className="text-red-500 text-sm mt-1">{requestForm.formState.errors.email.message}</p>
            )}
          </div>

          <Button 
            type="submit" 
            className="w-full flex items-center justify-center" 
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <TbLoader className="animate-spin h-5 w-5 mr-2" />
                <span>Enviando...</span>
              </>
            ) : (
              <>
                <TbMail className="h-5 w-5 mr-2" />
                <span>Enviar Código de Recuperación</span>
              </>
            )}
          </Button>

          <p className="text-center text-sm mt-4">
            <a 
              href="#" 
              onClick={(e) => {
                e.preventDefault();
                router.push('/auth/login');
              }}
              className="text-blue-600 hover:underline flex items-center justify-center"
            >
              <TbArrowLeft className="h-4 w-4 mr-1" />
              <span>Volver al login</span>
            </a>
          </p>
        </form>
      ) : (
        // Formulario de restablecimiento
        <form onSubmit={resetForm.handleSubmit(onResetSubmit)} className="space-y-4">
          <input 
            type="hidden" 
            {...resetForm.register('code')} 
          />

          <div>
            <Label htmlFor="recovery-email" className="flex items-center">
              <TbMail className="h-5 w-5 mr-2 text-gray-500" />
              Correo de recuperación
            </Label>
            <Input
              id="recovery-email"
              type="email"
              value={recoveryEmail || ''}
              disabled
            />
          </div>

          <div>
            <Label htmlFor="password" className="flex items-center">
              <TbLock className="h-5 w-5 mr-2 text-gray-500" />
              Nueva Contraseña
            </Label>
            <Input 
              id="password"
              type="password" 
              {...resetForm.register('password')} 
              className={resetForm.formState.errors.password ? 'border-red-500' : ''}
            />
            {resetForm.formState.errors.password && (
              <p className="text-red-500 text-sm mt-1">{resetForm.formState.errors.password.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="confirmPassword" className="flex items-center">
              <TbShieldLock className="h-5 w-5 mr-2 text-gray-500" />
              Confirmar Contraseña
            </Label>
            <Input 
              id="confirmPassword"
              type="password" 
              {...resetForm.register('confirmPassword')} 
              className={resetForm.formState.errors.confirmPassword ? 'border-red-500' : ''}
            />
            {resetForm.formState.errors.confirmPassword && (
              <p className="text-red-500 text-sm mt-1">{resetForm.formState.errors.confirmPassword.message}</p>
            )}
          </div>

          <Button 
            type="submit" 
            className="w-full flex items-center justify-center" 
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <TbLoader className="animate-spin h-5 w-5 mr-2" />
                <span>Restableciendo...</span>
              </>
            ) : (
              <>
                <TbCheck className="h-5 w-5 mr-2" />
                <span>Restablecer Contraseña</span>
              </>
            )}
          </Button>
        </form>
      )}
    </div>
  );
}
