import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import CandidateScreenshot from "./CandidateScreenshot";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const SRC = "http://api.test/api/v1/candidates/c1/screenshot";

it("evidence shows the screenshot with alt text", () => {
  renderWithProviders(
    <CandidateScreenshot
      src={SRC}
      title="Passport"
      fetchedAt="2020-01-01T00:00:00Z"
    />,
  );

  const image = screen.getByRole("img", { name: /Passport/ });
  expect(image).toHaveAttribute("src", SRC);
  expect(image).toHaveAttribute("loading", "lazy");
  expect(screen.getByText(/^Captured /)).toBeInTheDocument();
});

it("evidence falls back when the screenshot is missing", () => {
  renderWithProviders(
    <CandidateScreenshot src={null} title="Passport" fetchedAt={null} />,
  );

  expect(screen.getByText("No screenshot available yet")).toBeInTheDocument();
  expect(screen.queryByRole("img")).toBeNull();
});

it("evidence falls back when the screenshot fails to load", () => {
  renderWithProviders(
    <CandidateScreenshot src={SRC} title="Passport" fetchedAt={null} />,
  );

  fireEvent.error(screen.getByRole("img", { name: /Passport/ }));

  expect(screen.getByText("No screenshot available yet")).toBeInTheDocument();
  expect(screen.queryByRole("img")).toBeNull();
});

it("the screenshot frame is vertically scrollable", () => {
  renderWithProviders(
    <CandidateScreenshot src={SRC} title="Passport" fetchedAt={null} />,
  );

  const frame = screen.getByRole("img", { name: /Passport/ }).parentElement;

  expect(frame).toHaveStyle({ overflowY: "auto" });
  expect(window.getComputedStyle(frame as Element).maxHeight).not.toBe("none");
});

it("the image renders at its natural aspect ratio", () => {
  renderWithProviders(
    <CandidateScreenshot src={SRC} title="Passport" fetchedAt={null} />,
  );

  const image = screen.getByRole("img", { name: /Passport/ });

  expect(image).toHaveStyle({ width: "100%", height: "auto" });
  expect(window.getComputedStyle(image).objectFit).not.toBe("cover");
});
