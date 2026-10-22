import { Field, Input } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

export interface TextFieldState {
  value: string;
  onChange: (value: string) => void;
}

export interface TitleFieldsProps {
  title: TextFieldState;
  titleOther: TextFieldState;
  invalid: boolean;
}

export default function TitleFields({
  title,
  titleOther,
  invalid,
}: TitleFieldsProps) {
  const { t } = useLocale();

  return (
    <>
      <Field.Root invalid={invalid}>
        <Field.Label>{t("suggest.document_title")}</Field.Label>
        <Input
          value={title.value}
          onChange={(e) => title.onChange(e.target.value)}
        />
        {invalid ? (
          <Field.ErrorText>{t("errors.validation_error")}</Field.ErrorText>
        ) : null}
      </Field.Root>
      <Field.Root>
        <Field.Label>{t("suggest.document_title_other")}</Field.Label>
        <Input
          value={titleOther.value}
          onChange={(e) => titleOther.onChange(e.target.value)}
        />
      </Field.Root>
    </>
  );
}
