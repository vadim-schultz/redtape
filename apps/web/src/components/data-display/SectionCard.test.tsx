import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import SectionCard from "./SectionCard";

const RAW_VALUE = /#[0-9a-f]{3,8}\b|rgba?\(|\d+px \d+px/i;

function shell() {
  return screen.getByRole("region");
}

it("SectionCard · renders a raised title and toolbar surface", () => {
  renderWithProviders(
    <SectionCard title="Services" toolbar={<button>Filter</button>}>
      Body text
    </SectionCard>,
  );

  const style = getComputedStyle(shell());

  expect(screen.getByRole("heading", { name: "Services" })).toBeInTheDocument();
  expect(shell()).toHaveAccessibleName("Services");
  expect(shell()).toContainElement(screen.getByRole("button"));
  expect(shell()).toHaveTextContent("Body text");
  expect(style.backgroundColor).toBe("var(--chakra-colors-surface)");
  expect(style.boxShadow).toBe("var(--chakra-shadows-shell)");
  expect(style.borderColor).toBe("var(--chakra-colors-border)");
});

it("SectionCard · does not invent raw visual values or a hover lift", () => {
  renderWithProviders(<SectionCard title="Services">Body</SectionCard>);

  const style = getComputedStyle(shell());

  expect(style.backgroundColor).not.toMatch(RAW_VALUE);
  expect(style.boxShadow).not.toMatch(RAW_VALUE);
  expect(style.borderColor).not.toMatch(RAW_VALUE);
  expect(style.transform).toBe("");
  expect(style.transitionDuration).not.toBe("var(--chakra-durations-normal)");
});

it("SectionCard · without a title the shell is a plain unlabelled group", () => {
  renderWithProviders(<SectionCard>Body only</SectionCard>);

  expect(screen.queryByRole("region")).not.toBeInTheDocument();
  expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  expect(screen.getByText("Body only")).toBeInTheDocument();
});
