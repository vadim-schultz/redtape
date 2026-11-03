import { Stack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import SectionCard from "../../../components/data-display/SectionCard";
import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCandidateDetailResponse } from "../types";
import DocumentHeader from "./DocumentHeader";
import DocumentMentionsTable from "./DocumentMentionsTable";

/** Candidate detail body: header and mentions, then the sections the page passes in. */
export default function DocumentDetail({
  data,
  children,
}: {
  data: DiscoveryCandidateDetailResponse;
  children: ReactNode;
}) {
  const { t } = useLocale();

  return (
    <Stack gap={6} align="stretch">
      <DocumentHeader
        candidate={data.candidate}
        jurisdictionName={data.jurisdiction_name_i18n}
      />
      <SectionCard title={t("discovery_admin.document.mentions_title")}>
        <DocumentMentionsTable mentions={data.mentions} />
      </SectionCard>
      {children}
    </Stack>
  );
}
