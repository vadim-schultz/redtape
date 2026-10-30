import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import CandidateDetailSkeleton from "./CandidateDetailSkeleton";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("candidate detail skeleton is a busy status region", () => {
  renderWithProviders(<CandidateDetailSkeleton />);

  const region = screen.getByRole("status", { name: "Loading..." });
  expect(region).toHaveAttribute("aria-busy", "true");
});
