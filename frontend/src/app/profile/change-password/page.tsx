"use client"

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {changePassword as apiChangePassword} from '@/services/api';
import { useRouter } from 'next/navigation';
import { useApiError } from '@/hooks/useApiError';
import { TbLock, TbLockOpen, TbDeviceFloppy, TbArrowLeft } from "react-icons/tb";
import { ROUTES } from '@/routes/routePaths';
import { useAuth } from '@/hooks/useAuth';
import { updateAuthCookies } from '@/utils/authSync';

const changePasswordSchema = z.object({
  oldPassword: z.string().min(1, { message: 'La contraseña actual es obligatoria' }),
  newPassword: z.string()
    .min(8, { message: 'La contraseña debe tener al menos 8 caracteres' })
    .regex(/[A-Z]/, { message: 'Debe contener al menos una letra mayúscula' })
    .regex(/[a-z]/, { message: 'Debe contener al menos una letra minúscula' })
    .regex(/[0-9]/, { message: 'Debe contener al menos un número' })
    .regex(/[@$!%*?&]/, { message: 'Debe contener al menos un carácter especial (@$!%*?&)' }),
  confirmPassword: z.string()
    .min(1, { message: 'La confirmación de contraseña es obligatoria' }),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: 'Las contraseñas no coinciden',
  path: ['confirmPassword'],
});

type ChangePasswordInputs = z.infer<typeof changePasswordSchema>;

export default function ChangePassword() {
  const { register, handleSubmit, reset, formState: { errors } } = useForm<ChangePasswordInputs>({
    resolver: zodResolver(changePasswordSchema),
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const { error, handleApiError, clearError } = useApiError();
  const router = useRouter();
  const { refreshProfile } = useAuth();

  const onSubmit = async (data: ChangePasswordInputs) => {
    setIsSubmitting(true);
    clearError();
    setSuccessMessage(null);

    try {
      const response = await apiChangePassword({
        old_password: data.oldPassword,
        new_password: data.newPassword,
        confirm_password: data.confirmPassword
      });

      sessionStorage.setItem('access_token', response.access);
      sessionStorage.setItem('refresh_token', response.refresh);
      updateAuthCookies(response.access);
      await refreshProfile();
     
      setSuccessMessage('Contraseña actualizada con éxito');
      reset();
      
      // Redirigir al perfil después de 2 segundos
      setTimeout(() => {
        router.push(ROUTES.PROTECTED.PROFILE);
      }, 2000);
    } catch (err) {
      handleApiError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-md">
      <h1 className="text-2xl font-bold text-center mb-6 flex items-center justify-center">
        <TbLock className="w-6 h-6 mr-2" />
        Cambiar Contraseña
      </h1>
      
      {successMessage && (
        <Alert variant="default" className="mb-4">
          <AlertDescription>{successMessage}</AlertDescription>
        </Alert>
      )}
      
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      )}
      
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="currentPassword" className="flex items-center">
            <TbLockOpen className="w-5 h-5 mr-2 text-gray-500" />
            Contraseña Actual
          </Label>
          <Input 
            id="currentPassword"
            type="password" 
            {...register('oldPassword')} 
            className={errors.oldPassword ? 'border-red-500' : ''}
          />
          {errors.oldPassword && (
            <p className="text-red-500 text-sm mt-1">{errors.oldPassword.message}</p>
          )}
        </div>
        
        <div>
          <Label htmlFor="newPassword" className="flex items-center">
            <TbLock className="w-5 h-5 mr-2 text-gray-500" />
            Nueva Contraseña
          </Label>
          <Input 
            id="newPassword"
            type="password" 
            {...register('newPassword')} 
            className={errors.newPassword ? 'border-red-500' : ''}
          />
          {errors.newPassword && (
            <p className="text-red-500 text-sm mt-1">{errors.newPassword.message}</p>
          )}
        </div>
        
        <div>
          <Label htmlFor="confirmPassword" className="flex items-center">
            <TbLock className="w-5 h-5 mr-2 text-gray-500" />
            Confirmar Nueva Contraseña
          </Label>
          <Input 
            id="confirmPassword"
            type="password" 
            {...register('confirmPassword')} 
            className={errors.confirmPassword ? 'border-red-500' : ''}
          />
          {errors.confirmPassword && (
            <p className="text-red-500 text-sm mt-1">{errors.confirmPassword.message}</p>
          )}
        </div>
        
        <div className="flex justify-between mt-6">
          <Button 
            type="button" 
            variant="outline"
            onClick={() => router.back()}
            className="flex items-center"
          >
            <TbArrowLeft className="mr-2" />
            Cancelar
          </Button>
          <Button 
            type="submit" 
            disabled={isSubmitting}
            className="flex items-center"
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin h-5 w-5 mr-3 text-white" viewBox="0 0 24 24"></svg>
                Cambiando...
              </>
            ) : (
              <>
                <TbDeviceFloppy className="mr-2" />
                Cambiar Contraseña
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
