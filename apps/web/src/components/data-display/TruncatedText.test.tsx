import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { emotionRules } from "../../test/emotionRules";
import { renderWithProviders } from "../../test/renderWithProviders";
import TruncatedText from "./TruncatedText";

const LONG = "A".repeat(200);

it("TruncatedText clips the text at the given width and keeps it whole in the DOM", () => {
  renderWithProviders(<TruncatedText maxWidth="24rem">{LONG}</TruncatedText>);

  const rules = emotionRules(screen.getByText(LONG));
  expect(rules).toContain("max-width: 24rem");
  expect(rules).toContain("overflow: hidden");
  expect(rules).toContain("text-overflow: ellipsis");
  expect(rules).toContain("white-space: nowrap");
});

it("TruncatedText shows the full text in a tooltip on hover", async () => {
  const { user } = renderWithProviders(
    <TruncatedText maxWidth="24rem">{LONG}</TruncatedText>,
  );

  await user.hover(screen.getByText(LONG));

  expect(await screen.findByRole("tooltip")).toHaveTextContent(LONG);
});

it("TruncatedText shows the full text in a tooltip on keyboard focus", async () => {
  const { user } = renderWithProviders(
    <TruncatedText maxWidth="24rem" to="/documents/1">
      {LONG}
    </TruncatedText>,
  );

  await user.tab();

  expect(screen.getByRole("link", { name: LONG })).toHaveFocus();
  expect(await screen.findByRole("tooltip")).toHaveTextContent(LONG);
});

it("TruncatedText stays a link named by its full text when given a target", () => {
  renderWithProviders(
    <TruncatedText maxWidth="24rem" to="/documents/1">
      {LONG}
    </TruncatedText>,
  );

  expect(screen.getByRole("link", { name: LONG })).toHaveAttribute(
    "href",
    "/documents/1",
  );
});

it("TruncatedText renders no tooltip and no link until asked", () => {
  renderWithProviders(<TruncatedText maxWidth="24rem">{LONG}</TruncatedText>);

  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});
