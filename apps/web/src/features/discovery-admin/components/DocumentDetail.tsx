import { Heading, Stack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCandidateDetailResponse } from "../types";
import DocumentHeader from "./DocumentHeader";
import DocumentMentionsTable from "./DocumentMentionsTable";

/** Candidate detail body: header, mentions and the emit and evidence slots. */
export default function DocumentDetail({
  data,
  emit,
  evidence,
}: {
  data: DiscoveryCandidateDetailResponse;
  emit: ReactNode;
  evidence: ReactNode;
}) {
  const { t } = useLocale();

  return (
    <Stack gap={6} align="stretch">
      <DocumentHeader
        candidate={data.candidate}
        jurisdictionName={data.jurisdiction_name_i18n}
      />
      <Stack gap={2} align="stretch">
        <Heading size="sm">
          {t("discovery_admin.document.mentions_title")}
        </Heading>
        <DocumentMentionsTable mentions={data.mentions} />
      </Stack>
      {evidence}
      {emit}
    </Stack>
  );
}
