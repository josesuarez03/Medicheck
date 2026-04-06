"use client";

import { CredentialResponse, GoogleLogin } from "@react-oauth/google";
import { TbBrandGoogle, TbLoader } from "react-icons/tb";

type GoogleAuthButtonProps = {
  loading?: boolean;
  mode?: "signin" | "signup";
  onSuccess: (credentialResponse: CredentialResponse) => void | Promise<void>;
  onError: () => void;
};

export default function GoogleAuthButton({
  loading = false,
  mode = "signin",
  onSuccess,
  onError,
}: GoogleAuthButtonProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-card shadow-sm transition hover:border-primary/30 hover:shadow-md">
      <div className="pointer-events-none flex items-center gap-3 px-4 py-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          {loading ? <TbLoader className="h-5 w-5 animate-spin" /> : <TbBrandGoogle className="h-5 w-5" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold leading-none text-foreground">Continuar con Google</p>
          <p className="mt-1 text-sm text-muted-foreground">Acceso rápido sin contraseña</p>
        </div>
        <div className="shrink-0 text-muted-foreground">›</div>
      </div>

      <div className="google-auth-overlay absolute inset-0 overflow-hidden rounded-2xl">
        <GoogleLogin
          onSuccess={onSuccess}
          onError={onError}
          useOneTap={false}
          auto_select={false}
          theme="outline"
          text={mode === "signup" ? "signup_with" : "signin_with"}
          shape="rectangular"
          size="large"
          locale="es"
          context={mode === "signup" ? "signup" : "signin"}
          ux_mode="popup"
        />
      </div>
    </div>
  );
}
