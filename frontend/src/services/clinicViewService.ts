import {
  chatEpisodes,
  clinicalSummary,
  doctorAppointments,
  doctorDashboardSummary,
  doctorPatients,
  patientAppointments,
  patientTimeline,
  validationQueue,
} from "@/services/clinicMockData";

export async function getDoctorDashboardSummary() {
  return Promise.resolve(doctorDashboardSummary);
}

export async function getDoctorPatients() {
  return Promise.resolve(doctorPatients);
}

export async function getValidationQueue() {
  return Promise.resolve(validationQueue);
}

export async function getDoctorAppointments() {
  return Promise.resolve(doctorAppointments);
}

export async function getPatientAppointments() {
  return Promise.resolve(patientAppointments);
}

export async function getChatEpisodes() {
  return Promise.resolve(chatEpisodes);
}

export async function getClinicalSummary() {
  return Promise.resolve(clinicalSummary);
}

export async function getPatientTimeline() {
  return Promise.resolve(patientTimeline);
}
