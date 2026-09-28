import { useState, type FormEvent } from "react";
import { Button, Field, Stack, Textarea } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CreateSuggestionRequest } from "../../types";
import type { FieldErrors } from "../../utils/parseFieldErrors";

import MunicipalityField from "./MunicipalityField";
import TaxonomyChips from "./TaxonomyChips";
import TitleFields from "./TitleFields";
import UrlField from "./UrlField";

export interface SuggestionFormProps {
  onSubmit: (request: CreateSuggestionRequest) => void;
  isSending: boolean;
  fieldErrors?: FieldErrors;
}

const OTHER_LOCALE: Record<string, string> = { en: "de", de: "en" };
const MAX_URL_LENGTH = 500;

function isValidUrl(value: string): boolean {
  return /^https?:\/\//.test(value) && value.length <= MAX_URL_LENGTH;
}

function buildTitleI18n(locale: string, title: string, titleOther: string) {
  const otherLocale = OTHER_LOCALE[locale] ?? "en";
  return {
    [locale]: title.trim(),
    ...(titleOther.trim() ? { [otherLocale]: titleOther.trim() } : {}),
  };
}

export default function SuggestionForm({
  onSubmit,
  isSending,
  fieldErrors = {},
}: SuggestionFormProps) {
  const { t, locale } = useLocale();
  const [municipalityCode, setMunicipalityCode] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [titleOther, setTitleOther] = useState("");
  const [officialUrl, setOfficialUrl] = useState("");
  const [description, setDescription] = useState("");
  const [domainCodes, setDomainCodes] = useState<string[]>([]);
  const [situationCodes, setSituationCodes] = useState<string[]>([]);
  const [touched, setTouched] = useState(false);

  const titleInvalid = touched && !title.trim();
  const urlInvalid = touched && !isValidUrl(officialUrl);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched(true);
    if (!municipalityCode || !title.trim() || !isValidUrl(officialUrl)) return;

    onSubmit({
      municipality_code: municipalityCode,
      payload: {
        title_i18n: buildTitleI18n(locale, title, titleOther),
        ...(description.trim()
          ? { description_i18n: { [locale]: description.trim() } }
          : {}),
        official_url: officialUrl,
        domain_codes: domainCodes,
        situation_codes: situationCodes,
      },
    });
  }

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap={4}>
        <MunicipalityField onMunicipalityChange={setMunicipalityCode} />
        <TitleFields
          title={title}
          onTitleChange={setTitle}
          titleOther={titleOther}
          onTitleOtherChange={setTitleOther}
          invalid={titleInvalid}
        />
        <UrlField
          value={officialUrl}
          onChange={setOfficialUrl}
          invalid={urlInvalid}
          errorMessage={fieldErrors.official_url}
        />
        <Field.Root>
          <Field.Label>{t("suggest.description")}</Field.Label>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Field.Root>
        <TaxonomyChips
          domainCodes={domainCodes}
          onDomainsChange={setDomainCodes}
          situationCodes={situationCodes}
          onSituationsChange={setSituationCodes}
        />
        <Button type="submit" loading={isSending} disabled={isSending}>
          {t("suggest.submit")}
        </Button>
      </Stack>
    </form>
  );
}
