import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import LoadingShell from "./LoadingShell";

it("LoadingShell · shows the brand and an announced spinner in the stored locale", () => {
  window.localStorage.setItem("locale", "de");
  render(<LoadingShell />);

  expect(screen.getByText("Redtape")).toBeInTheDocument();
  expect(screen.getByRole("status", { name: "Lädt..." })).toBeInTheDocument();
});

it("LoadingShell · falls back to English for other locales", () => {
  window.localStorage.setItem("locale", "fr");
  render(<LoadingShell />);

  expect(
    screen.getByRole("status", { name: "Loading..." }),
  ).toBeInTheDocument();
});
