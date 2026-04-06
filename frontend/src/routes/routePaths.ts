export const ROUTES = {
    // Public routes
    PUBLIC: {
      HOME: '/',
      LOGIN: '/auth/login',
      REGISTER: '/auth/register',
      PROFILE_TYPE: '/auth/profile-type',
      RECOVER_PASSWORD: '/auth/recover-password',
      PROFILE_COMPLETE: '/auth/complete',
      VERIFY_CODE: '/auth/verify-code',
    },
    
    // Protected routes
    PROTECTED: {
      DASHBOARD: '/dashboard',
      PROFILE: '/profile',
      PROFILE_EDIT: '/profile/edit',
      PROFILE_CHANGE_PASSWORD: '/profile/change-password',
      PROFILE_DELETE_ACCOUNT: '/profile/delete-account',
      CHAT: '/chat',
      CHAT_SESSIONS: '/chat/sessions',
      MEDICAL_DATA: '/medical-data',
      TRIAGE_HISTORY: '/triage-history',
      APPOINTMENTS: '/appointments',
      APPOINTMENT_NEW: '/appointments/new',
    },
    
    // Doctor-specific routes
    DOCTOR: {
      DASHBOARD: '/doctor/dashboard',
      PATIENTS: '/doctor/patients',
      VALIDATIONS: '/doctor/validations',
      APPOINTMENTS: '/doctor/appointments',
    }
  };
  
  // Navigation data for sidebar and menus
  export const NAVIGATION_ITEMS = {
    // Main navigation
    main: [
      { name: 'Dashboard', path: ROUTES.PROTECTED.DASHBOARD, icon: 'HomeIcon' },
      { name: 'Chat', path: ROUTES.PROTECTED.CHAT, icon: 'ChatBubbleOvalLeftIcon' },
      { name: 'Historial', path: ROUTES.PROTECTED.TRIAGE_HISTORY, icon: 'ActivityIcon' },
      { name: 'Datos clínicos', path: ROUTES.PROTECTED.MEDICAL_DATA, icon: 'ClipboardDocumentListIcon' },
      { name: 'Citas', path: ROUTES.PROTECTED.APPOINTMENTS, icon: 'CalendarIcon' },
    ],
    
    // Doctor-specific navigation
    doctor: [
      { name: 'Dashboard', path: ROUTES.DOCTOR.DASHBOARD, icon: 'HomeIcon' },
      { name: 'Patients', path: ROUTES.DOCTOR.PATIENTS, icon: 'UserGroupIcon' },
      { name: 'Validaciones', path: ROUTES.DOCTOR.VALIDATIONS, icon: 'ClipboardCheckIcon' },
      { name: 'Citas', path: ROUTES.DOCTOR.APPOINTMENTS, icon: 'CalendarIcon' },
    ],
    
    // Profile-related links
    profile: [
      { name: 'Edit Profile', path: ROUTES.PROTECTED.PROFILE_EDIT, icon: 'PencilIcon' },
      { name: 'Change Password', path: ROUTES.PROTECTED.PROFILE_CHANGE_PASSWORD, icon: 'LockClosedIcon' },
      { name: 'Delete Account', path: ROUTES.PROTECTED.PROFILE_DELETE_ACCOUNT, icon: 'TrashIcon' },
    ],
  };
