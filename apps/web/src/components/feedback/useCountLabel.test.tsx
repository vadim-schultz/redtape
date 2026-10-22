import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import { useCountLabel } from "./useCountLabel";

function Probe({ namespace, count }: { namespace: string; count: number }) {
  const countLabel = useCountLabel(namespace);

  return <p data-testid="label">{countLabel(count)}</p>;
}

function renderLabel(namespace: string, count: number) {
  renderWithProviders(<Probe namespace={namespace} count={count} />);
}

describe("useCountLabel", () => {
  it.each([
    ["documents", 1, "1 document"],
    ["documents", 0, "0 documents"],
    ["documents", 5, "5 documents"],
    ["suggestions", 1, "1 suggestion"],
    ["suggestions", 5, "5 suggestions"],
    ["discovery_admin.tasks", 1, "1 task"],
    ["discovery_admin.tasks", 0, "0 tasks"],
  ])("%s with %i reads %s", async (namespace, count, expected) => {
    renderLabel(namespace, count);

    expect(await screen.findByText(expected)).toBeInTheDocument();
  });

  it("falls back to the raw key for an unknown namespace without throwing", async () => {
    renderLabel("nope", 3);

    expect(await screen.findByText("nope.count_other")).toBeInTheDocument();
  });
});
