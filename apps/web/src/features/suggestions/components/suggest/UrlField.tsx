import { Field, Input } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

export interface UrlFieldProps {
  value: string;
  onChange: (value: string) => void;
  invalid: boolean;
  errorMessage?: string;
}

export default function UrlField({
  value,
  onChange,
  invalid,
  errorMessage,
}: UrlFieldProps) {
  const { t } = useLocale();

  return (
    <Field.Root invalid={invalid || Boolean(errorMessage)}>
      <Field.Label>{t("suggest.official_url")}</Field.Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
      {errorMessage ? (
        <Field.ErrorText>{errorMessage}</Field.ErrorText>
      ) : invalid ? (
        <Field.ErrorText>{t("errors.validation_error")}</Field.ErrorText>
      ) : null}
    </Field.Root>
  );
}
