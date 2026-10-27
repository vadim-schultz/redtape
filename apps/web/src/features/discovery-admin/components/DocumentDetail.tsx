import { Heading, Stack } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCandidateDetailResponse } from "../types";
import DocumentHeader from "./DocumentHeader";
import DocumentMentionsTable from "./DocumentMentionsTable";

/** Candidate detail body: header and mentions. */
export default function DocumentDetail({
  data,
}: {
  data: DiscoveryCandidateDetailResponse;
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
    </Stack>
  );
}
