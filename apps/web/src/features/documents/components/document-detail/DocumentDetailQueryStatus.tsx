import { Alert, Box, Heading, Skeleton, Text } from "@chakra-ui/react";

import type { DocumentDetail } from "../../types";

import DocumentHeader from "./DocumentHeader";
import DocumentBreadcrumb from "./DocumentBreadcrumb";
import RequirementsList from "./requirements/RequirementsList";
import RequirementsEmpty from "./requirements/RequirementsEmpty";

export interface DocumentDetailQueryStatusProps {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
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

function ErrorAlert() {
  return (
    <Alert.Root status="error">
      <Alert.Indicator />
      <Alert.Title>Server error</Alert.Title>
    </Alert.Root>
  );
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
    document,
    requirementsTitle,
    noRequirementsLabel,
    officialSourceTitle,
  } = props;

  if (isLoading) return <LoadingSkeleton />;
  if (isError) return <ErrorAlert />;
  if (!document) return null;

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
