import { screen, waitFor } from "@testing-library/react";
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
    <CandidateEvidence candidate={candidate} screenshotUrl={SCREENSHOT_URL} />,
  );
}

it("the sources accordion is collapsed by default", () => {
  renderEvidence();

  const trigger = screen.getByRole("button", { name: "Sources" });
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("list")).toBeNull();
});

it("the accordion trigger is titled Sources", () => {
  renderEvidence();

  expect(screen.getByRole("button", { name: "Sources" })).toBeVisible();
});

it("expanding the accordion reveals the sources list", async () => {
  const { user } = renderEvidence();

  const trigger = screen.getByRole("button", { name: "Sources" });
  trigger.focus();
  await user.keyboard("{Enter}");

  expect(trigger).toHaveAttribute("aria-expanded", "true");
  const link = screen.getByRole("link", { name: "Apply for a passport" });
  expect(link).toHaveAttribute("href", "https://portal.example/passport");
  expect(screen.getByText("Required")).toBeVisible();
  expect(screen.getByText("A valid passport is required.")).toBeVisible();
});

it("the screenshot stays outside the accordion and always visible", async () => {
  const { user } = renderEvidence();

  expect(screen.getByRole("img", { name: /Passport/ })).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Sources" }));

  expect(screen.getByRole("img", { name: /Passport/ })).toBeVisible();
});

it("collapsing after expanding hides the sources again", async () => {
  const { user } = renderEvidence();

  const trigger = screen.getByRole("button", { name: "Sources" });
  await user.click(trigger);
  expect(trigger).toHaveAttribute("aria-expanded", "true");

  trigger.focus();
  await user.keyboard(" ");

  expect(trigger).toHaveAttribute("aria-expanded", "false");
  await waitFor(() => expect(screen.queryByRole("list")).toBeNull());
});
