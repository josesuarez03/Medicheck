"use client"

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {updateUserProfile as apiUpdateProfile} from '@/services/api';
import { 
  TbArrowLeft, 
  TbDeviceFloppy, 
  TbUser, 
  TbCalendar, 
  TbPhone, 
  TbHome, 
  TbGenderMale, 
  TbBriefcase, 
  TbStethoscope, 
  TbCertificate, 
  TbAlertTriangle
} from "react-icons/tb";
import { ROUTES } from '@/routes/routePaths';

const profileSchema = z.object({
    first_name: z.string()
        .min(1, { message: 'El nombre es obligatorio' })
        .regex(/^[a-zA-Z\s]+$/, { message: 'El nombre solo puede contener letras y espacios' })
        .max(50, { message: 'El nombre no puede exceder los 50 caracteres' }),
    last_name: z.string()
        .min(1, { message: 'El apellido es obligatorio' })
        .regex(/^[a-zA-Z\s]+$/, { message: 'El apellido solo puede contener letras y espacios' })
        .max(50, { message: 'El apellido no puede exceder los 50 caracteres' }),
    fecha_nacimiento: z.string().min(1, { message: 'La fecha de nacimiento es obligatoria' }),
    telefono: z.string().min(1, { message: 'El teléfono es obligatorio' })
        .regex(/^\d{10}$/, { message: 'El teléfono debe tener 10 dígitos' }),
    direccion: z.string().min(1, { message: 'La dirección es obligatoria' }),
    genero: z.string().min(1, { message: 'El género es obligatorio' }),
});

const patientSchema = z.object({
    ocupacion: z.string().min(1, { message: 'La ocupación es obligatoria' }),
    allergies: z.string().optional(),
});

const doctorSchema = z.object({
    especialidad: z.string().min(1, { message: 'La especialidad es obligatoria' }),
    numero_licencia: z.string().min(1, { message: 'El número de licencia es obligatorio' })
        .regex(/^\d+$/, { message: 'El número de licencia debe ser un número' }),
});

type ProfileFormData = z.infer<typeof profileSchema> &
    Partial<z.infer<typeof patientSchema>> &
    Partial<z.infer<typeof doctorSchema>>;

export default function EditProfile(){
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const getValidationSchema = () => {
        if (user?.tipo === 'patient') {
            return profileSchema.merge(patientSchema);
        } else if (user?.tipo === 'doctor') {
            return profileSchema.merge(doctorSchema);
        }
        return profileSchema;
    };

    const { register, handleSubmit, formState: { errors }, setValue, control } = useForm<ProfileFormData>({
        resolver: zodResolver(getValidationSchema()),
    });

    useEffect(() => {
            if (user) {
                setValue('first_name', user.first_name || '');
                setValue('last_name', user.last_name || '');
                setValue('fecha_nacimiento', user.fecha_nacimiento || '');
                setValue('telefono', user.telefono || '');
                setValue('direccion', user.direccion || '');
                setValue('genero', user.genero || '');
    
                if (user.tipo === 'patient' && user.patient) {
                    setValue('ocupacion' as keyof ProfileFormData, user.patient.ocupacion || '');
                    setValue('allergies' as keyof ProfileFormData, user.patient.allergies || '');
                } else if (user.tipo === 'doctor' && user.doctor) {
                    setValue('especialidad' as keyof ProfileFormData, user.doctor.especialidad || '');
                    setValue('numero_licencia' as keyof ProfileFormData, user.doctor.numero_licencia || '');
                }
            }
        }, [user, setValue]);
    
    useEffect(() => {
        // Redirigir si no hay usuario autenticado
        if (!authLoading && !user) {
            router.push(ROUTES.PUBLIC.LOGIN);
        }
    }, [user, authLoading, router]);

     const onSubmit = async (data: ProfileFormData) => {
        setLoading(true);
        setError(null);
        setSuccess(false);

        try {
            // Utilizamos la función importada en lugar de API.put
            await apiUpdateProfile(data);
            setSuccess(true);
            // Mostrar mensaje de éxito por un momento antes de redirigir
            setTimeout(() => {
                router.push(ROUTES.PROTECTED.PROFILE);
            }, 1500);
        } catch (err: unknown) {
            setError('Error al actualizar el perfil. Inténtalo de nuevo.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    const handleCancel = () => {
        router.push(ROUTES.PROTECTED.PROFILE);
    };

    if (authLoading) {
        return (
            <div className="flex justify-center items-center h-screen">
                <svg className="animate-spin h-5 w-5 mr-3 text-white" viewBox="0 0 24 24"></svg>
                <span className="text-white">Cargando...</span>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="text-center p-10">
                <Alert>
                    <AlertDescription>
                        Debes iniciar sesión para editar tu perfil.
                        <Button
                            onClick={() => router.push(ROUTES.PUBLIC.LOGIN)}
                            className="ml-4"
                        >
                            Iniciar Sesión
                        </Button>
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <Card className="w-full max-w-3xl mx-auto shadow-lg">
                <CardHeader>
                    <div className="flex items-center justify-between mb-4">
                        {/* Botón reutilizable para volver */}
                        <Button
                            variant="ghost"
                            onClick={handleCancel}
                            className="flex items-center"
                            aria-label="Volver al perfil"
                        >
                            <TbArrowLeft className="mr-2" />
                            Volver
                        </Button>
                        {/* Icono del perfil */}
                        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary/12 text-primary text-2xl">
                            <TbUser />
                        </div>
                    </div>
                    {/* Título del encabezado */}
                    <CardTitle className="text-center text-xl font-semibold">
                        Editar Perfil
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
                    {success && (
                        <Alert className="mb-4 bg-green-50 border-green-500">
                            <AlertDescription className="text-green-700">
                                ¡Perfil actualizado correctamente! Redirigiendo...
                            </AlertDescription>
                        </Alert>
                    )}
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <Label className="flex items-center">
                                    <TbUser className="w-5 h-5 mr-2 text-gray-500" />
                                    Nombre
                                </Label>
                                <Input {...register('first_name')} />
                                {errors.first_name && <p className="text-red-500 text-sm">{errors.first_name.message}</p>}
                            </div>
                            <div>
                                <Label className="flex items-center">
                                    <TbUser className="w-5 h-5 mr-2 text-gray-500" />
                                    Apellido
                                </Label>
                                <Input {...register('last_name')} />
                                {errors.last_name && <p className="text-red-500 text-sm">{errors.last_name.message}</p>}
                            </div>
                            <div>
                                <Label className="flex items-center">
                                    <TbCalendar className="w-5 h-5 mr-2 text-gray-500" />
                                    Fecha de Nacimiento
                                </Label>
                                <Input type="date" {...register('fecha_nacimiento')} />
                                {errors.fecha_nacimiento && <p className="text-red-500 text-sm">{errors.fecha_nacimiento.message}</p>}
                            </div>
                            <div>
                                <Label className="flex items-center">
                                    <TbGenderMale className="w-5 h-5 mr-2 text-gray-500" />
                                    Género
                                </Label>
                                <Controller
                                    name="genero"
                                    control={control}
                                    render={({ field }) => (
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Selecciona tu género" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="masculino">Masculino</SelectItem>
                                                <SelectItem value="femenino">Femenino</SelectItem>
                                                <SelectItem value="otro">Otro</SelectItem>
                                                <SelectItem value="prefiero_no_decir">Prefiero no decir</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    )}
                                />
                                {errors.genero && <p className="text-red-500 text-sm">{errors.genero.message}</p>}
                            </div>
                            <div>
                                <Label className="flex items-center">
                                    <TbPhone className="w-5 h-5 mr-2 text-gray-500" />
                                    Teléfono
                                </Label>
                                <Input {...register('telefono')} />
                                {errors.telefono && <p className="text-red-500 text-sm">{errors.telefono.message}</p>}
                            </div>
                            <div>
                                <Label className="flex items-center">
                                    <TbHome className="w-5 h-5 mr-2 text-gray-500" />
                                    Dirección
                                </Label>
                                <Input {...register('direccion')} />
                                {errors.direccion && <p className="text-red-500 text-sm">{errors.direccion.message}</p>}
                            </div>
                        </div>

                        {/* Campos adicionales según el tipo de usuario */}
                        {user.tipo === 'patient' && (
                            <div className="border-t pt-6 mt-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center">
                                    <TbBriefcase className="w-5 h-5 mr-2 text-gray-700" />
                                    Información Médica
                                </h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <Label className="flex items-center">
                                            <TbBriefcase className="w-5 h-5 mr-2 text-gray-500" />
                                            Ocupación
                                        </Label>
                                        <Input {...register('ocupacion')} />
                                        {errors.ocupacion && <p className="text-red-500 text-sm">{errors.ocupacion?.message}</p>}
                                    </div>
                                    <div className="md:col-span-2">
                                        <Label className="flex items-center">
                                            <TbAlertTriangle className="w-5 h-5 mr-2 text-gray-500" />
                                            Alergias (opcional)
                                        </Label>
                                        <Textarea {...register('allergies')} rows={3} />
                                    </div>
                                </div>
                            </div>
                        )}

                        {user.tipo === 'doctor' && (
                            <div className="border-t pt-6 mt-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center">
                                    <TbStethoscope className="w-5 h-5 mr-2 text-gray-700" />
                                    Información Profesional
                                </h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <Label className="flex items-center">
                                            <TbStethoscope className="w-5 h-5 mr-2 text-gray-500" />
                                            Especialidad
                                        </Label>
                                        <Input {...register('especialidad')} />
                                        {errors.especialidad && <p className="text-red-500 text-sm">{errors.especialidad?.message}</p>}
                                    </div>
                                    <div>
                                        <Label className="flex items-center">
                                            <TbCertificate className="w-5 h-5 mr-2 text-gray-500" />
                                            Número de Licencia
                                        </Label>
                                        <Input {...register('numero_licencia')} />
                                        {errors.numero_licencia && <p className="text-red-500 text-sm">{errors.numero_licencia?.message}</p>}
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="flex justify-end space-x-4 pt-6">
                            <Button type="button" variant="outline" onClick={handleCancel} className="flex items-center">
                                <TbArrowLeft className="mr-2" />
                                Cancelar
                            </Button>
                            <Button
                                type="submit"
                                disabled={loading}
                                className="min-w-[150px] flex items-center"
                            >
                                {loading ? (
                                    <div className="flex items-center justify-center">
                                        <svg className="animate-spin h-5 w-5 mr-3 text-white" viewBox="0 0 24 24"></svg>
                                        <span className="text-white">Guardando...</span>
                                    </div>
                                ) : (
                                    <div className="flex items-center">
                                        <TbDeviceFloppy className="mr-2" />
                                        Guardar Cambios
                                    </div>
                                )}
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}
