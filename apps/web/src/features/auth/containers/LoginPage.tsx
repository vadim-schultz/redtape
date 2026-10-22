import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { LuUserX } from "react-icons/lu";

import EmptyStateCard from "../../../components/feedback/EmptyStateCard";
import { useLocale } from "../../../contexts/LocaleContext";
import { useAuth, type AuthStatus } from "../contexts/AuthContext";
import LoginForm from "../components/login/LoginForm";
import LoginSentNotice from "../components/login/LoginSentNotice";
import LoginErrorNotice from "../components/login/LoginErrorNotice";

type FormState = "idle" | "sending" | "sent" | "error";
type LoginLocationState = { from?: { pathname: string } };

function redirectTarget(state: unknown): string {
  return (state as LoginLocationState | null)?.from?.pathname ?? "/documents";
}

function renderLoginContent({
  status,
  formState,
  onSubmit,
  unavailableTitle,
}: {
  status: AuthStatus;
  formState: FormState;
  onSubmit: (email: string) => void;
  unavailableTitle: string;
}) {
  if (status === "unconfigured")
    return (
      <EmptyStateCard icon={LuUserX} content={{ title: unavailableTitle }} />
    );
  if (status === "authenticated") return null;
  if (formState === "sent") return <LoginSentNotice />;

  return (
    <>
      {formState === "error" ? <LoginErrorNotice /> : null}
      <LoginForm onSubmit={onSubmit} isSending={formState === "sending"} />
    </>
  );
}

export default function LoginPage() {
  const { status, signIn } = useAuth();
  const { t } = useLocale();
  const location = useLocation();
  const navigate = useNavigate();
  const [formState, setFormState] = useState<FormState>("idle");

  useEffect(() => {
    if (status !== "authenticated") return;
    navigate(redirectTarget(location.state), { replace: true });
  }, [status, location.state, navigate]);

  async function handleSubmit(email: string) {
    setFormState("sending");
    try {
      await signIn(email);
      setFormState("sent");
    } catch {
      setFormState("error");
    }
  }

  return renderLoginContent({
    status,
    formState,
    onSubmit: (email) => void handleSubmit(email),
    unavailableTitle: t("auth.unavailable"),
  });
}
