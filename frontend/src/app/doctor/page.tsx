import { redirect } from "next/navigation";
import { ROUTES } from "@/routes/routePaths";

export default function DoctorIndexPage() {
  redirect(ROUTES.DOCTOR.DASHBOARD);
}
