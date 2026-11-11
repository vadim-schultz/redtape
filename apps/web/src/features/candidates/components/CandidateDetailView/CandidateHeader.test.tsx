import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import {
  candidateDetailFixture,
  translationSummaryFixture,
} from "../../../../test/candidateFixtures";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import CandidateHeader from "./CandidateHeader";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("candidate detail renders header, description and attribution", () => {
  renderWithProviders(<CandidateHeader candidate={candidateDetailFixture()} />);

  expect(
    screen.getByRole("heading", { level: 1, name: "Passport" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Proof of identity.")).toBeInTheDocument();
  expect(
    screen.getByText("From the source page: Apply for a passport"),
  ).toBeInTheDocument();
  expect(screen.getByText("Identity")).toBeInTheDocument();
  expect(screen.getByText("Identity").closest("a")).toHaveAttribute(
    "href",
    "/documents?category=identity-and-documents",
  );
});

it("candidate detail omits an absent description", () => {
  const candidate = candidateDetailFixture({
    description: null,
    description_source: null,
  });
  renderWithProviders(<CandidateHeader candidate={candidate} />);

  expect(screen.getByRole("heading", { name: "Passport" })).toBeInTheDocument();
  expect(screen.queryByRole("blockquote")).toBeNull();
  expect(screen.queryByText(/From the source page/)).toBeNull();
});

it("candidate detail shows the translation trigger beside the title when a translation exists", async () => {
  renderWithProviders(
    <CandidateHeader
      candidate={candidateDetailFixture({
        translation: translationSummaryFixture(),
      })}
    />,
  );

  const trigger = await screen.findByRole("button", {
    name: "Show translation",
  });
  const heading = screen.getByRole("heading", { level: 1, name: "Passport" });

  expect(heading.contains(trigger)).toBe(false);
  expect(heading.parentElement).toContainElement(trigger);
});

it("candidate detail has no translation trigger without a translation", () => {
  renderWithProviders(
    <CandidateHeader
      candidate={candidateDetailFixture({ translation: null })}
    />,
  );

  expect(screen.queryByRole("button", { name: "Show translation" })).toBeNull();
});
