import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { emotionRules } from "../../../../test/emotionRules";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DiscoveryCoverageResponse } from "../../types";
import { baseCoverage, emptyCoverage, finishedRun } from "./coverageFixture";
import CoverageSummary from "./CoverageSummary";

beforeEach(() => window.localStorage.setItem("locale", "en"));

function renderSummary(coverage: DiscoveryCoverageResponse) {
  return renderWithProviders(<CoverageSummary coverage={coverage} />);
}

/** The text of every cell in the row that starts with ``label`` in the named table. */
function rowTexts(tableName: string, label: string | RegExp): string[] {
  const table = screen.getByRole("table", { name: tableName });
  const row = within(table).getByRole("row", {
    name: typeof label === "string" ? new RegExp(`^${label}\\b`) : label,
  });
  return within(row)
    .getAllByRole("cell")
    .map((cell) => cell.textContent ?? "");
}

it("coverage renders source, queue, outcome, and artifact metrics as grouped rows", () => {
  renderSummary(baseCoverage);

  expect(rowTexts("Catalogue rows by source", "govdata")).toEqual([
    "govdata",
    "2",
  ]);
  expect(rowTexts("Task queue", "Pending tasks")).toEqual([
    "Pending tasks",
    "3",
  ]);
  expect(rowTexts("Task queue", "Emit-ready")).toEqual(["Emit-ready", "4"]);
  expect(rowTexts("Task queue", "Fetch attempts")).toEqual([
    "Fetch attempts",
    "12",
  ]);
  expect(rowTexts("Tasks by kind", "harvest_payload")).toEqual([
    "harvest_payload",
    "3",
    "1",
    "1",
    "0",
    "1Needs attention",
  ]);
  expect(rowTexts("Document candidates", "Candidate mentions")).toEqual([
    "Candidate mentions",
    "9",
  ]);
  expect(rowTexts("Extraction outcomes", "Extracted")).toEqual([
    "Extracted",
    "7",
  ]);
  expect(rowTexts("Artifact storage", "HTML snapshots")).toEqual([
    "HTML snapshots",
    "3",
    "3 GB",
  ]);
  expect(rowTexts("Failed tasks by source", "fim")).toEqual(["fim", "1"]);
});

it("coverage renders the last successful run as labelled rows", () => {
  renderSummary({ ...baseCoverage, last_successful_run: finishedRun });

  expect(rowTexts("Last successful run", "Claimed")).toEqual(["Claimed", "5"]);
  expect(rowTexts("Last successful run", "Stop reason")).toEqual([
    "Stop reason",
    "batch_limit",
  ]);
  expect(screen.queryByText("No successful run recorded yet.")).toBeNull();
});

it("coverage renders unknown source and kind keys", () => {
  renderSummary({
    ...baseCoverage,
    by_source: { future_portal: 4 } as DiscoveryCoverageResponse["by_source"],
    task_counts_by_kind: {
      future_kind: {
        total: 1,
        pending: 1,
        claimed: 0,
        completed: 0,
        failed: 0,
      },
    },
    failures_by_source: {
      future_portal: 2,
    } as DiscoveryCoverageResponse["failures_by_source"],
    artifacts: {
      by_kind: { pdf_copy: { count: 1, bytes: 10 } },
      total_bytes: 10,
      bytes_cap: 0,
    },
  });

  expect(rowTexts("Catalogue rows by source", "future_portal")[1]).toBe("4");
  expect(rowTexts("Tasks by kind", "future_kind")[1]).toBe("1");
  expect(rowTexts("Failed tasks by source", "future_portal")[1]).toBe("2");
  expect(rowTexts("Artifact storage", "pdf_copy")).toEqual([
    "pdf_copy",
    "1",
    "10 B",
  ]);
});

it("coverage renders an explicit empty state for no sources or failures", () => {
  renderSummary(emptyCoverage);

  const inTable = (name: string, text: string) =>
    expect(
      within(screen.getByRole("table", { name })).getByText(text),
    ).toBeInTheDocument();
  inTable("Catalogue rows by source", "No catalogue rows yet.");
  inTable("Failed tasks by source", "No failed tasks.");
  inTable("Tasks by kind", "No task kinds yet.");
  inTable("Last successful run", "No successful run recorded yet.");
  expect(screen.queryByText(/Last successful run:/)).toBeNull();
});

it("coverage flags failed, stale and zero queue counts distinctly", () => {
  const { unmount } = renderSummary(baseCoverage);
  expect(rowTexts("Task queue", "Failed tasks")[1]).toBe("1Needs attention");
  expect(rowTexts("Task queue", "Stale leases")[1]).toBe("2Needs attention");
  expect(rowTexts("Task queue", "Completed tasks")[1]).toBe("3");
  unmount();

  renderSummary(emptyCoverage);
  expect(rowTexts("Task queue", "Failed tasks")[1]).toBe("0");
  expect(screen.queryByText("Needs attention")).toBeNull();
});

it("coverage tables are static and advertise no sort or filter controls", () => {
  renderSummary(baseCoverage);

  expect(screen.queryAllByRole("textbox")).toHaveLength(0);
  expect(screen.queryAllByRole("button")).toHaveLength(0);
});

const GIB = 1024 ** 3;
const EIGHTY_PERCENT = Math.ceil(8 * GIB * 0.8);

function withStoredBytes(totalBytes: number): DiscoveryCoverageResponse {
  return {
    ...baseCoverage,
    artifacts: { ...baseCoverage.artifacts, total_bytes: totalBytes },
  };
}

it("coverage view shows artifact bytes against the cap without a warning below 80 percent", () => {
  renderSummary(withStoredBytes(3 * GIB));

  expect(rowTexts("Artifact storage", "Screenshots")).toEqual([
    "Screenshots",
    "2",
    "1 KB",
  ]);
  expect(rowTexts("Artifact storage", "Total stored")).toEqual([
    "Total stored",
    "5",
    "3 GB of 8 GB",
  ]);
  expect(screen.queryByText("Nearly full")).not.toBeInTheDocument();
});

it("coverage view warns once the stored bytes reach 80 percent of the cap", () => {
  const { rerender } = renderSummary(withStoredBytes(EIGHTY_PERCENT - 1));
  expect(screen.queryByText("Nearly full")).not.toBeInTheDocument();

  rerender(<CoverageSummary coverage={withStoredBytes(EIGHTY_PERCENT)} />);

  expect(screen.getByText("Nearly full")).toHaveClass("chakra-badge");
  expect(rowTexts("Artifact storage", "Total stored")[2]).toBe(
    "6.4 GB of 8 GBNearly full",
  );
});

it("coverage view tolerates a zero storage cap without warning", () => {
  renderSummary({
    ...baseCoverage,
    artifacts: { by_kind: {}, total_bytes: 10, bytes_cap: 0 },
  });

  expect(screen.queryByText("Nearly full")).not.toBeInTheDocument();
});

it("coverage aligns metric values to the end while labels stay at the start", () => {
  renderSummary(baseCoverage);

  const table = screen.getByRole("table", { name: "Tasks by kind" });
  const [label, ...values] = within(table).getAllByRole("columnheader");
  const row = within(table).getByRole("row", { name: /^harvest_payload\b/ });
  const [labelCell, firstValue, , , , badged] =
    within(row).getAllByRole("cell");

  expect(emotionRules(label)).not.toContain("text-align: end");
  expect(emotionRules(labelCell)).not.toContain("text-align: end");
  for (const header of values) {
    expect(emotionRules(header)).toContain("text-align: end");
  }
  expect(emotionRules(firstValue)).toContain("text-align: end");
  expect(emotionRules(badged.firstElementChild!)).toContain(
    "justify-content: flex-end",
  );
});
