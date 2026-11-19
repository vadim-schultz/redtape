import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import {
  candidateDetailFixture,
  sourceFixture,
} from "../../../../test/candidateFixtures";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import CandidateEvidence from "./CandidateEvidence";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const SCREENSHOT_URL = "http://api.test/api/v1/candidates/c1/screenshot";

const candidate = candidateDetailFixture({
  title: "Passport",
  sources: [sourceFixture()],
});

function renderEvidence() {
  return renderWithProviders(
    <CandidateEvidence
      candidate={candidate}
      captures={[{ src: SCREENSHOT_URL, fetchedAt: "2026-10-01T10:00:00Z" }]}
    />,
  );
}

it("evidence renders the screenshot without owning a sources accordion", () => {
  renderEvidence();

  expect(screen.getByRole("img", { name: /Passport/ })).toBeVisible();
  expect(screen.queryByRole("button", { name: "Sources" })).toBeNull();
});
