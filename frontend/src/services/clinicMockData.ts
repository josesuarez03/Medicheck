import type {
  AppointmentListItem,
  ChatEpisodeSummary,
  ClinicalSummaryView,
  DoctorDashboardSummary,
  DoctorPatientListItem,
  PatientTimelineEntry,
  ValidationQueueItem,
} from "@/types/clinic";

export const doctorDashboardSummary: DoctorDashboardSummary = {
  assignedPatients: 42,
  pendingValidations: 8,
  pendingAppointments: 5,
  recentAlerts: 3,
};

export const validationQueue: ValidationQueueItem[] = [
  {
    id: "VAL-301",
    patientName: "Laura García",
    timestamp: "Hoy · 09:40",
    triageLevel: "moderado",
    summary: "Dolor de garganta, fiebre y empeoramiento en 24 horas. El sistema sugiere revisión clínica y posible cita breve.",
    actionHint: "Revisar y decidir si agendar en 24-48h.",
  },
  {
    id: "VAL-302",
    patientName: "Carlos Núñez",
    timestamp: "Hoy · 08:55",
    triageLevel: "urgente",
    summary: "Dolor torácico con sensación de falta de aire. El flujo escala el episodio y marca prioridad inmediata.",
    actionHint: "Confirmar orientación urgente.",
  },
  {
    id: "VAL-303",
    patientName: "Marta Ríos",
    timestamp: "Ayer · 18:10",
    triageLevel: "leve",
    summary: "Consulta libre por resfriado común, sin señales de alarma y con sugerencia de seguimiento remoto.",
    actionHint: "Validar cierre o seguimiento remoto.",
  },
];

export const doctorPatients: DoctorPatientListItem[] = [
  {
    id: "PAT-1001",
    patientName: "Laura García",
    ageLabel: "34 años",
    triageLevel: "moderado",
    status: "Pendiente de validación",
    lastActivity: "Hace 2 h",
    nextAction: "Revisar episodio y proponer cita",
  },
  {
    id: "PAT-1002",
    patientName: "Carlos Núñez",
    ageLabel: "58 años",
    triageLevel: "urgente",
    status: "Escalado clínico",
    lastActivity: "Hace 45 min",
    nextAction: "Confirmar derivación urgente",
  },
  {
    id: "PAT-1003",
    patientName: "Marta Ríos",
    ageLabel: "29 años",
    triageLevel: "leve",
    status: "Seguimiento remoto",
    lastActivity: "Ayer",
    nextAction: "Validar cierre",
  },
  {
    id: "PAT-1004",
    patientName: "José Martín",
    ageLabel: "47 años",
    triageLevel: "moderado",
    status: "Cita pendiente",
    lastActivity: "Hace 1 día",
    nextAction: "Asignar hueco de consulta",
  },
];

export const patientAppointments: AppointmentListItem[] = [
  {
    id: "APP-410",
    patientName: "Laura García",
    dateLabel: "14 abril 2026",
    timeLabel: "10:30",
    mode: "Videoconsulta",
    professional: "Dra. Andrea Romero",
    status: "confirmada",
    reason: "Revisión por empeoramiento de síntomas respiratorios.",
  },
  {
    id: "APP-411",
    patientName: "Laura García",
    dateLabel: "22 abril 2026",
    timeLabel: "09:10",
    mode: "Presencial",
    professional: "Dr. Marcos León",
    status: "seguimiento",
    reason: "Seguimiento posterior a episodio moderado.",
  },
];

export const doctorAppointments: AppointmentListItem[] = [
  {
    id: "APP-510",
    patientName: "Carlos Núñez",
    dateLabel: "Hoy",
    timeLabel: "12:15",
    mode: "Telefónica",
    professional: "Dr. Irene Salas",
    status: "pendiente",
    reason: "Confirmación de prioridad y orientación clínica.",
  },
  {
    id: "APP-511",
    patientName: "José Martín",
    dateLabel: "Mañana",
    timeLabel: "08:45",
    mode: "Presencial",
    professional: "Dr. Irene Salas",
    status: "confirmada",
    reason: "Consulta breve tras recomendación de revisión médica.",
  },
];

export const chatEpisodes: ChatEpisodeSummary[] = [
  {
    id: "SES-1001",
    patientName: "Laura García",
    dateLabel: "Hoy",
    triageLevel: "moderado",
    recommendation: "Se recomienda cita de revisión en 24-48 horas.",
    summary: "Fiebre, dolor de garganta y malestar progresivo.",
    suggestedPriority: "24-48h",
  },
  {
    id: "SES-1002",
    patientName: "Carlos Núñez",
    dateLabel: "Hoy",
    triageLevel: "urgente",
    recommendation: "Señales de alarma detectadas. Buscar atención urgente.",
    summary: "Dolor torácico y disnea reportados durante la conversación.",
    suggestedPriority: "Inmediata",
  },
  {
    id: "SES-1003",
    patientName: "Marta Ríos",
    dateLabel: "Ayer",
    triageLevel: "leve",
    recommendation: "Seguimiento remoto y control de síntomas.",
    summary: "Síntomas catarrales sin red flags clínicas.",
    suggestedPriority: "Seguimiento",
  },
];

export const patientTimeline: PatientTimelineEntry[] = [
  {
    id: "TL-1",
    title: "Triaje conversacional completado",
    description: "Se registró un episodio con recomendación de revisión clínica breve.",
    dateLabel: "Hoy · 09:40",
    kind: "triaje",
  },
  {
    id: "TL-2",
    title: "Resumen clínico validado",
    description: "La profesional confirmó el contexto y dejó observaciones para seguimiento.",
    dateLabel: "Hoy · 10:10",
    kind: "validacion",
  },
  {
    id: "TL-3",
    title: "Cita generada",
    description: "Se propuso videoconsulta para revisar la evolución de síntomas.",
    dateLabel: "Hoy · 10:18",
    kind: "cita",
  },
];

export const clinicalSummary: ClinicalSummaryView = {
  patientName: "Laura García",
  ageLabel: "34 años",
  occupation: "Administrativa",
  triageLevel: "moderado",
  allergies: "No alergias registradas",
  medications: "Ibuprofeno ocasional",
  medicalHistory: "Sin antecedentes relevantes registrados",
  context: "Paciente con fiebre, dolor de garganta y malestar general en progresión desde ayer.",
  lastRecommendation: "Revisión clínica breve y control de evolución.",
  validationStatus: "Pendiente de revisión médica final",
};
