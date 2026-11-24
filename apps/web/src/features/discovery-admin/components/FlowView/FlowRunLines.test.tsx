import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import { RunAge, StopReason } from "./FlowRunLines";
import { finishedRun } from "./flowFixture";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("a finished run shows its age and its stop reason", () => {
  renderWithProviders(
    <>
      <RunAge run={finishedRun("queue_empty")} />
      <StopReason run={finishedRun("queue_empty")} />
    </>,
  );

  expect(screen.getByText(/^Last run: /)).toBeVisible();
  expect(screen.getByText("Stop reason: queue empty")).toBeVisible();
});

it("a run that recorded no stop reason shows no stop reason line", () => {
  renderWithProviders(<StopReason run={finishedRun(null)} />);

  expect(screen.queryByText(/Stop reason/)).not.toBeInTheDocument();
});
