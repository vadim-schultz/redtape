import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import CandidateScreenshot from "./CandidateScreenshot";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const SRC = "http://api.test/api/v1/candidates/c1/screenshot";
const CAPTURE = { src: SRC, fetchedAt: "2020-01-01T00:00:00Z" };
const OLDER = {
  src: "http://api.test/api/v1/candidates/c1/screenshots/old",
  fetchedAt: "2019-01-01T00:00:00Z",
};

it("evidence shows the screenshot with alt text", () => {
  renderWithProviders(
    <CandidateScreenshot captures={[CAPTURE]} title="Passport" />,
  );

  const image = screen.getByRole("img", { name: /Passport/ });
  expect(image).toHaveAttribute("src", SRC);
  expect(image).toHaveAttribute("loading", "lazy");
  expect(screen.getByText(/^Captured /)).toBeInTheDocument();
});

it("evidence falls back when the screenshot is missing", () => {
  renderWithProviders(<CandidateScreenshot captures={[]} title="Passport" />);

  expect(screen.getByText("No screenshot available yet")).toBeInTheDocument();
  expect(screen.queryByRole("img")).toBeNull();
});

it("evidence falls back when the screenshot fails to load", () => {
  renderWithProviders(
    <CandidateScreenshot captures={[CAPTURE]} title="Passport" />,
  );

  fireEvent.error(screen.getByRole("img", { name: /Passport/ }));

  expect(screen.getByText("No screenshot available yet")).toBeInTheDocument();
  expect(screen.queryByRole("img")).toBeNull();
});

it("one capture renders no tab list", () => {
  renderWithProviders(
    <CandidateScreenshot captures={[CAPTURE]} title="Passport" />,
  );

  expect(screen.queryByRole("tablist")).toBeNull();
  expect(screen.getByRole("img", { name: /Passport/ })).toBeVisible();
});

it("two or more captures render the history as tabs", () => {
  renderWithProviders(
    <CandidateScreenshot captures={[CAPTURE, OLDER]} title="Passport" />,
  );

  expect(screen.getByRole("tablist")).toBeInTheDocument();
  expect(screen.getAllByRole("tab")).toHaveLength(2);
});

it("the screenshot frame is vertically scrollable", () => {
  renderWithProviders(
    <CandidateScreenshot captures={[CAPTURE]} title="Passport" />,
  );

  const frame = screen.getByRole("img", { name: /Passport/ }).parentElement;

  expect(frame).toHaveStyle({ overflowY: "auto" });
  expect(window.getComputedStyle(frame as Element).maxHeight).not.toBe("none");
});

it("the image renders at its natural aspect ratio", () => {
  renderWithProviders(
    <CandidateScreenshot captures={[CAPTURE]} title="Passport" />,
  );

  const image = screen.getByRole("img", { name: /Passport/ });

  expect(image).toHaveStyle({ width: "100%", height: "auto" });
  expect(window.getComputedStyle(image).objectFit).not.toBe("cover");
});
