import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { candidateDetailFixture } from "../../../../test/candidateFixtures";
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
  expect(screen.getByText("Moving")).toBeInTheDocument();
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
