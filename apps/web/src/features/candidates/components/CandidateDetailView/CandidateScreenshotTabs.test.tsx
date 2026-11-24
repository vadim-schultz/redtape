import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { formatDate } from "../../../../utils/format/formatDate";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import CandidateScreenshotTabs from "./CandidateScreenshotTabs";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const NEWEST = {
  src: "http://api.test/api/v1/candidates/c1/screenshots/new",
  fetchedAt: "2026-10-02T10:00:00Z",
};
const OLDER = {
  src: "http://api.test/api/v1/candidates/c1/screenshots/old",
  fetchedAt: "2026-09-01T10:00:00Z",
};

function renderTabs() {
  return renderWithProviders(
    <CandidateScreenshotTabs captures={[NEWEST, OLDER]} title="Passport" />,
  );
}

it("the newest tab is selected by default and shows the absolute date", () => {
  renderTabs();

  const [first, second] = screen.getAllByRole("tab");
  expect(first).toHaveAttribute("aria-selected", "true");
  expect(second).toHaveAttribute("aria-selected", "false");
  expect(first).toHaveAttribute("title", formatDate(NEWEST.fetchedAt, "en"));
});

it("only the active capture's image is in the DOM", () => {
  renderTabs();

  const images = screen.getAllByRole("img");
  expect(images).toHaveLength(1);
  expect(images[0]).toHaveAttribute("src", NEWEST.src);
});

it("a failed image shows the missing text on its tab only", async () => {
  const { user } = renderTabs();

  fireEvent.error(screen.getByRole("img"));

  expect(screen.getByText("No screenshot available yet")).toBeInTheDocument();
  expect(screen.getAllByRole("tab")).toHaveLength(2);
  await user.click(screen.getAllByRole("tab")[1]);
  expect(screen.getByRole("img")).toHaveAttribute("src", OLDER.src);
});

it("arrow keys move focus between tabs, and Enter chooses the tab reached", async () => {
  const { user } = renderTabs();
  const [first, second] = screen.getAllByRole("tab");

  first.focus();
  await user.keyboard("{ArrowRight}");

  // Zag moves focus on the next animation frame, so wait for the focus to land.
  await waitFor(() => expect(second).toHaveFocus());
  expect(screen.getByRole("img")).toHaveAttribute("src", NEWEST.src);

  await user.keyboard("{Enter}");

  await waitFor(() =>
    expect(screen.getByRole("img")).toHaveAttribute("src", OLDER.src),
  );
  expect(second).toHaveAttribute("aria-selected", "true");
});
