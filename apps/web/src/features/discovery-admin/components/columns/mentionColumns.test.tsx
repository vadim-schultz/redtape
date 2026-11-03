import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { DataTable } from "../../../../components/data-display/DataTable";
import { useLocale } from "../../../../contexts/LocaleContext";
import { mention } from "../../../../test/discoveryAdminFixtures";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import { mentionColumns } from "./mentionColumns";

beforeEach(() => window.localStorage.setItem("locale", "en"));

function Table({ items }: { items: ReturnType<typeof mention>[] }) {
  return (
    <DataTable
      label="Mentions"
      columns={mentionColumns(useLocale())}
      rows={{ items, getKey: (item) => item.id }}
    />
  );
}

it("mentionColumns · an empty condition and host render the placeholder", () => {
  renderWithProviders(
    <Table items={[mention({ condition: null, portal_url: null })]} />,
  );

  expect(screen.getAllByRole("cell", { name: "—" })).toHaveLength(2);
});
