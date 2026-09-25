import { Box, Heading, Skeleton, Text } from "@chakra-ui/react";
import { LuFileX } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import QueryError from "../../../../components/feedback/QueryError";
import { useLocale } from "../../../../contexts/LocaleContext";
import { ApiRequestError } from "../../../../services/api";
import type { DocumentDetail } from "../../types";

import DocumentHeader from "./DocumentHeader";
import DocumentBreadcrumb from "./DocumentBreadcrumb";
import RequirementsList from "./requirements/RequirementsList";
import RequirementsEmpty from "./requirements/RequirementsEmpty";

export interface DocumentDetailQueryStatusProps {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  document: DocumentDetail | undefined;
  requirementsTitle: string;
  noRequirementsLabel: string;
  officialSourceTitle: string;
}

function LoadingSkeleton() {
  return (
    <>
      <Skeleton height="28px" />
      <Skeleton mt={2} height="18px" />
    </>
  );
}

function DocumentNotFound() {
  const { t } = useLocale();

  return <EmptyStateCard icon={LuFileX} title={t("documents.not_found")} />;
}

function isNotFound(error: unknown) {
  return error instanceof ApiRequestError && error.status === 404;
}

function RequirementsSection({
  document,
  requirementsTitle,
  noRequirementsLabel,
}: {
  document: DocumentDetail;
  requirementsTitle: string;
  noRequirementsLabel: string;
}) {
  return (
    <Box mt={4}>
      <Heading textStyle="sectionHeader">{requirementsTitle}</Heading>
      {document.requirements?.length ? (
        <RequirementsList requirements={document.requirements} />
      ) : (
        <RequirementsEmpty label={noRequirementsLabel} />
      )}
    </Box>
  );
}

function OfficialSourceSection({ url, title }: { url: string; title: string }) {
  return (
    <Box mt={4}>
      <Heading textStyle="sectionHeader">{title}</Heading>
      <Text mt={1}>
        <a href={url} target="_blank" rel="noreferrer">
          {url}
        </a>
      </Text>
    </Box>
  );
}

function DocumentDetailContent({
  document,
  requirementsTitle,
  noRequirementsLabel,
  officialSourceTitle,
}: {
  document: DocumentDetail;
  requirementsTitle: string;
  noRequirementsLabel: string;
  officialSourceTitle: string;
}) {
  return (
    <>
      <DocumentHeader
        title={document.title}
        description={document.description}
      />
      <DocumentBreadcrumb nodes={document.jurisdiction_path ?? []} />
      <RequirementsSection
        document={document}
        requirementsTitle={requirementsTitle}
        noRequirementsLabel={noRequirementsLabel}
      />
      {document.official_url ? (
        <OfficialSourceSection
          url={document.official_url}
          title={officialSourceTitle}
        />
      ) : null}
    </>
  );
}

function renderQueryStatus(props: DocumentDetailQueryStatusProps) {
  const {
    isLoading,
    isError,
    error,
    onRetry,
    document,
    requirementsTitle,
    noRequirementsLabel,
    officialSourceTitle,
  } = props;

  if (isLoading) return <LoadingSkeleton />;
  if (isError && !isNotFound(error)) return <QueryError onRetry={onRetry} />;
  if (!document) return <DocumentNotFound />;

  return (
    <DocumentDetailContent
      document={document}
      requirementsTitle={requirementsTitle}
      noRequirementsLabel={noRequirementsLabel}
      officialSourceTitle={officialSourceTitle}
    />
  );
}

export default function DocumentDetailQueryStatus(
  props: DocumentDetailQueryStatusProps,
) {
  return renderQueryStatus(props);
}
