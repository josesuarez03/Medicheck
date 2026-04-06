'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  TbActivity,
  TbFileText,
  TbClock,
  TbClipboardCheck,
  TbAlertCircle,
  TbHistory,
  TbRefresh,
  TbPill,
  TbAlertTriangle,
  TbArrowRight,
} from 'react-icons/tb';
import API from '@/services/api';
import { ROUTES } from '@/routes/routePaths';
type PatientMedicalData = {
  triaje_level?: string | null;
  pain_scale?: number | null;
  medical_context?: string | null;
  allergies?: string | null;
  medications?: string | null;
  medical_history?: string | null;
  data_validated_at?: string | null;
  is_data_validated?: boolean;
};

export default function MedicalData() {
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [patientData, setPatientData] = useState<PatientMedicalData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const requestInFlightRef = useRef(false);

  const fetchPatientData = useCallback(async () => {
    const response = await API.get('patients/me/');
    return response.data;
  }, []);

  const getPatientData = useCallback(
    async (showRefreshing = false) => {
      if (requestInFlightRef.current) return;
      requestInFlightRef.current = true;
      try {
        showRefreshing ? setRefreshing(true) : setLoading(true);
        const data = await fetchPatientData();
        setPatientData(data);
        setError(null);
      } catch {
        setError('Error al cargar tus datos médicos');
      } finally {
        setLoading(false);
        setRefreshing(false);
        requestInFlightRef.current = false;
      }
    },
    [fetchPatientData]
  );

  useEffect(() => {
    if (!user?.id) {
      router.push(ROUTES.PUBLIC.LOGIN);
      return;
    }
    if (user?.tipo !== 'patient') {
      router.push(ROUTES.PROTECTED.DASHBOARD);
      return;
    }
    void getPatientData();
  }, [user?.id, user?.tipo]);

  const getTriageColorClass = (level: string | null | undefined) => {
    if (!level) return 'bg-gray-100 text-gray-800 border-gray-200';
    switch (level.toLowerCase()) {
      case 'urgente':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'moderado':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-green-100 text-green-800 border-green-200';
    }
  };

  const getPainScaleColorClass = (scale: number | null | undefined) => {
    if (scale === null || scale === undefined) return 'bg-gray-500';
    if (scale >= 7) return 'bg-red-500';
    if (scale >= 4) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="surface-card p-6">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-5 w-96 mt-3" />
        </div>
        <Card className="surface-card">
          <CardHeader>
            <Skeleton className="h-8 w-52" />
            <Skeleton className="h-5 w-40" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Alert variant="destructive">
          <TbAlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button onClick={() => getPatientData(true)} className="flex items-center gap-2">
          <TbRefresh className="h-4 w-4" />
          Intentar nuevamente
        </Button>
      </div>
    );
  }

  if (!patientData) return null;

  return (
    <div className="space-y-6">
      <section className="rounded-3xl overflow-hidden bg-gradient-to-r from-primary via-primary to-primary/90 text-white p-6 md:p-8 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">Mis datos médicos</h1>
            <p className="text-white/85 mt-2">Consulta tu estado clínico y actualiza tu información de salud.</p>
          </div>
          <Button
            variant="outline"
            className="border-white/35 bg-white/10 text-white hover:bg-white/20"
            onClick={() => getPatientData(true)}
            disabled={refreshing}
          >
            <TbRefresh className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Actualizando...' : 'Actualizar'}
          </Button>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="surface-card-interactive">
          <CardContent className="pt-5">
            <p className="text-sm text-muted-foreground">Estado de validación</p>
            <div className="mt-2">
              {patientData.is_data_validated ? (
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  <TbClipboardCheck className="h-3 w-3 mr-1" />
                  Validado por médico
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
                  Pendiente de validación
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="surface-card-interactive">
          <CardContent className="pt-5">
            <p className="text-sm text-muted-foreground">Nivel de triaje</p>
            <div className="mt-2">
              <Badge className={getTriageColorClass(patientData.triaje_level)}>
                {patientData.triaje_level ? `Triaje: ${patientData.triaje_level}` : 'Sin clasificación'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="surface-card-interactive">
          <CardContent className="pt-5">
            <p className="text-sm text-muted-foreground">Escala de dolor</p>
            <div className="flex items-center gap-3 mt-2">
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className={`h-2.5 rounded-full ${getPainScaleColorClass(patientData.pain_scale)}`}
                  style={{ width: `${((patientData.pain_scale || 0) / 10) * 100}%` }}
                />
              </div>
              <span className="text-sm font-semibold">{patientData.pain_scale ?? 0}/10</span>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[1.3fr_1fr] gap-4">
        <Card className="surface-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TbFileText className="h-5 w-5 text-primary" />
              Información médica
            </CardTitle>
            <CardDescription>Resumen clínico actual y observaciones registradas.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {[
              {
                icon: <TbFileText className="h-4 w-4 text-muted-foreground" />,
                title: 'Contexto médico',
                value: patientData.medical_context || 'No hay información disponible',
              },
              {
                icon: <TbAlertTriangle className="h-4 w-4 text-muted-foreground" />,
                title: 'Alergias',
                value: patientData.allergies || 'No se han registrado alergias',
              },
              {
                icon: <TbPill className="h-4 w-4 text-muted-foreground" />,
                title: 'Medicamentos',
                value: patientData.medications || 'No se han registrado medicamentos',
              },
              {
                icon: <TbHistory className="h-4 w-4 text-muted-foreground" />,
                title: 'Historial médico',
                value: patientData.medical_history || 'No se ha registrado historial médico',
              },
            ].map((block, idx) => (
              <div key={block.title}>
                <div className="surface-card-interactive p-4">
                  <h3 className="font-medium mb-2 flex items-center gap-2">
                    {block.icon}
                    {block.title}
                  </h3>
                  <p className="text-muted-foreground">{block.value}</p>
                </div>
                {idx < 3 && <Separator className="my-4" />}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="surface-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TbActivity className="h-5 w-5 text-primary" />
              Última actividad
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="surface-card-interactive p-4">
              <p className="text-sm text-muted-foreground">Última validación</p>
              <p className="mt-2 flex items-center gap-2">
                <TbClock className="h-4 w-4" />
                {patientData.data_validated_at
                  ? new Date(patientData.data_validated_at).toLocaleDateString('es-ES', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : 'Sin validaciones recientes'}
              </p>
            </div>
            <Button
              onClick={() => router.push(ROUTES.PROTECTED.TRIAGE_HISTORY)}
              className="w-full justify-between"
            >
              Ver historial completo
              <TbArrowRight className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
