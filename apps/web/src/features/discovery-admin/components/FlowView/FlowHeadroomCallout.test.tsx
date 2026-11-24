import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import FlowHeadroomCallout from "./FlowHeadroomCallout";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("the allotment callout names a resource with headroom and ready work", () => {
  renderWithProviders(
    <FlowHeadroomCallout
      headroom={[{ resource: "neurons", stage: "card_translation" }]}
    />,
  );

  expect(screen.getByRole("note")).toHaveTextContent(
    "AI neurons has unused headroom while Card translation has ready work.",
  );
});

it("no callout when the headroom is used", () => {
  renderWithProviders(<FlowHeadroomCallout headroom={[]} />);

  expect(screen.queryByRole("note")).not.toBeInTheDocument();
});
