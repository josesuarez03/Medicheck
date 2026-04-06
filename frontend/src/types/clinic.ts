export type TriageTone = "leve" | "moderado" | "urgente";

export interface AppointmentListItem {
  id: string;
  patientName: string;
  dateLabel: string;
  timeLabel: string;
  mode: string;
  professional: string;
  status: "pendiente" | "confirmada" | "seguimiento";
  reason: string;
}

export interface ValidationQueueItem {
  id: string;
  patientName: string;
  timestamp: string;
  triageLevel: TriageTone;
  summary: string;
  actionHint: string;
}

export interface ChatEpisodeSummary {
  id: string;
  patientName: string;
  dateLabel: string;
  triageLevel: TriageTone;
  recommendation: string;
  summary: string;
  suggestedPriority: string;
}

export interface DoctorDashboardSummary {
  assignedPatients: number;
  pendingValidations: number;
  pendingAppointments: number;
  recentAlerts: number;
}

export interface DoctorPatientListItem {
  id: string;
  patientName: string;
  ageLabel: string;
  triageLevel: TriageTone;
  status: string;
  lastActivity: string;
  nextAction: string;
}

export interface PatientTimelineEntry {
  id: string;
  title: string;
  description: string;
  dateLabel: string;
  kind: "triaje" | "validacion" | "cita";
}

export interface ClinicalSummaryView {
  patientName: string;
  ageLabel: string;
  occupation: string;
  triageLevel: TriageTone;
  allergies: string;
  medications: string;
  medicalHistory: string;
  context: string;
  lastRecommendation: string;
  validationStatus: string;
}
