// src/utils/router.ts
'use client';

import { useRouter } from 'next/navigation';
import { ROUTES } from '@/routes/routePaths';

export function useAppRouter() {
  const router = useRouter();

  // Navigation helpers
  const navigate = {
    // Public routes
    toLogin: (from?: string) => {
      const path = ROUTES.PUBLIC.LOGIN;
      if (from) {
        router.push(`${path}?from=${encodeURIComponent(from)}`);
      } else {
        router.push(path);
      }
    },
    toHome: () => router.push(ROUTES.PUBLIC.HOME),
    toRegister: () => router.push(ROUTES.PUBLIC.REGISTER),
    toProfileType: () => router.push(ROUTES.PUBLIC.PROFILE_TYPE),
    toCompleteProfile: () => router.push(ROUTES.PUBLIC.PROFILE_COMPLETE),
    toRecoverPassword: (fromLogin = true) => {
      const path = ROUTES.PUBLIC.RECOVER_PASSWORD;
      if (fromLogin) {
        router.push(`${path}?fromLogin=true`);
      } else {
        router.push(path);
      }
    },
    toVerifyCode: () => router.push(ROUTES.PUBLIC.VERIFY_CODE),

    // Protected routes
    toDashboard: () => router.push(ROUTES.PROTECTED.DASHBOARD),
    toProfile: () => router.push(ROUTES.PROTECTED.PROFILE),
    toProfileComplete: () => router.push(ROUTES.PUBLIC.PROFILE_COMPLETE),
    toEditProfile: () => router.push(ROUTES.PROTECTED.PROFILE_EDIT),
    toChangePassword: () => router.push(ROUTES.PROTECTED.PROFILE_CHANGE_PASSWORD),
    toDeleteAccount: () => router.push(ROUTES.PROTECTED.PROFILE_DELETE_ACCOUNT),
    toChat: () => router.push(ROUTES.PROTECTED.CHAT),
    toMedicalData: () => router.push(ROUTES.PROTECTED.MEDICAL_DATA),
    toTriageHistory: () => router.push(ROUTES.PROTECTED.TRIAGE_HISTORY),
    toAppointments: () => router.push(ROUTES.PROTECTED.APPOINTMENTS),

    // Doctor routes
    toDoctorDashboard: () => router.push(ROUTES.DOCTOR.DASHBOARD),
    toPatients: () => router.push(ROUTES.DOCTOR.PATIENTS),
    toDoctorValidations: () => router.push(ROUTES.DOCTOR.VALIDATIONS),
    toDoctorAppointments: () => router.push(ROUTES.DOCTOR.APPOINTMENTS),
  };

  return {
    router,
    navigate,
  };
}
