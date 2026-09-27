import { useState, type FormEvent } from "react";
import { Button, Field, Input, Stack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

export interface LoginFormProps {
  onSubmit: (email: string) => void;
  isSending: boolean;
}

function isValidEmail(value: string): boolean {
  return value.trim().length > 0 && value.includes("@");
}

export default function LoginForm({ onSubmit, isSending }: LoginFormProps) {
  const { t } = useLocale();
  const [email, setEmail] = useState("");
  const [touched, setTouched] = useState(false);
  const invalid = touched && !isValidEmail(email);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched(true);
    if (isValidEmail(email)) onSubmit(email);
  }

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap={4}>
        <Field.Root invalid={invalid}>
          <Field.Label>{t("auth.email")}</Field.Label>
          <Input
            type="email"
            value={email}
            placeholder={t("auth.email_placeholder")}
            onChange={(event) => setEmail(event.target.value)}
          />
          {invalid ? (
            <Field.ErrorText>{t("errors.validation_error")}</Field.ErrorText>
          ) : null}
        </Field.Root>
        <Button type="submit" loading={isSending}>
          {t("auth.send_link")}
        </Button>
      </Stack>
    </form>
  );
}
