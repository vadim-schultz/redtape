import { Field, Input } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

export interface TitleFieldsProps {
  title: string;
  onTitleChange: (value: string) => void;
  titleOther: string;
  onTitleOtherChange: (value: string) => void;
  invalid: boolean;
}

export default function TitleFields({
  title,
  onTitleChange,
  titleOther,
  onTitleOtherChange,
  invalid,
}: TitleFieldsProps) {
  const { t } = useLocale();

  return (
    <>
      <Field.Root invalid={invalid}>
        <Field.Label>{t("suggest.document_title")}</Field.Label>
        <Input value={title} onChange={(e) => onTitleChange(e.target.value)} />
        {invalid ? (
          <Field.ErrorText>{t("errors.validation_error")}</Field.ErrorText>
        ) : null}
      </Field.Root>
      <Field.Root>
        <Field.Label>{t("suggest.document_title_other")}</Field.Label>
        <Input
          value={titleOther}
          onChange={(e) => onTitleOtherChange(e.target.value)}
        />
      </Field.Root>
    </>
  );
}
