import { screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import {
  json,
  stubTranslationApi,
  translationCalls,
} from "../../../test/candidatesApiStub";
import {
  translationSummaryFixture,
  translationTextFixture,
} from "../../../test/candidateFixtures";
import { elementCss } from "../../../test/elementCss";
import { renderWithProviders } from "../../../test/renderWithProviders";
import type { TranslationSummary } from "../../../services/candidateTranslationApi";
import TranslationPopover from "./TranslationPopover";

beforeEach(() => window.localStorage.setItem("locale", "en"));

function renderPopover(summary: TranslationSummary | null) {
  return renderWithProviders(
    <TranslationPopover
      candidateId="c1"
      summary={summary}
      label="Pasaport Antrag"
    />,
  );
}

const trigger = () => screen.queryByRole("button", { name: "Show translation" });

it("popover · the trigger appears only when a translation exists and opens the translated title and description", async () => {
  stubTranslationApi(() => json(translationTextFixture()));
  const { user } = renderPopover(translationSummaryFixture());

  await user.click(await screen.findByRole("button", { name: "Show translation" }));

  expect(
    await screen.findByRole("heading", { name: "Pasaport başvurusu" }),
  ).toBeVisible();
  expect(screen.getByText("Kimlik kanıtı.")).toBeVisible();
});

it("popover · sets lang on the translated content and shows the machine-translation note", async () => {
  stubTranslationApi(() => json(translationTextFixture()));
  const { user } = renderPopover(translationSummaryFixture());

  await user.click(await screen.findByRole("button", { name: "Show translation" }));

  expect(
    await screen.findByRole("heading", { name: "Pasaport başvurusu" }),
  ).toHaveAttribute("lang", "tr");
  expect(screen.getByText("Kimlik kanıtı.")).toHaveAttribute("lang", "tr");
  expect(
    screen.getByText(
      "Machine translation, may contain errors. The German original is authoritative.",
    ),
  ).toBeVisible();
  expect(screen.queryByText(/original has changed/i)).toBeNull();
});

it("popover · shows the stale note when the German original changed", async () => {
  stubTranslationApi(() => json(translationTextFixture({ stale: true })));
  const { user } = renderPopover(translationSummaryFixture({ stale: true }));

  await user.click(await screen.findByRole("button", { name: "Show translation" }));

  expect(
    await screen.findByText(/The German original has changed since/),
  ).toBeVisible();
});

it("popover · the dialog is named after the German original", async () => {
  stubTranslationApi(() => json(translationTextFixture()));
  const { user } = renderPopover(translationSummaryFixture());

  await user.click(await screen.findByRole("button", { name: "Show translation" }));

  expect(
    await screen.findByRole("dialog", { name: "Pasaport Antrag" }),
  ).toBeVisible();
});

it("popover · the first open requests the stored text once, shows loading then content; a second open makes no request", async () => {
  let release: (response: Response) => void = () => undefined;
  const fetchMock = stubTranslationApi(
    () => new Promise<Response>((resolve) => (release = resolve)),
  );
  const { user } = renderPopover(translationSummaryFixture());
  await screen.findByRole("button", { name: "Show translation" });
  expect(translationCalls(fetchMock)).toHaveLength(0);

  await user.click(screen.getByRole("button", { name: "Show translation" }));
  expect(await screen.findByText("Loading translation…")).toBeVisible();
  release(json(translationTextFixture()));
  await screen.findByRole("heading", { name: "Pasaport başvurusu" });

  await user.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await user.click(screen.getByRole("button", { name: "Show translation" }));
  await screen.findByRole("heading", { name: "Pasaport başvurusu" });

  const calls = translationCalls(fetchMock);
  expect(calls).toHaveLength(1);
  expect(calls[0].pathname).toBe("/api/v1/candidates/c1/translation");
  expect(calls[0].searchParams.get("locale")).toBe("tr");
});

it("popover · keyboard: Enter and Space open, Escape closes and focus returns to the trigger", async () => {
  stubTranslationApi(() => json(translationTextFixture()));
  const { user } = renderPopover(translationSummaryFixture());
  const button = await screen.findByRole("button", { name: "Show translation" });

  button.focus();
  await user.keyboard("{Enter}");
  await screen.findByRole("heading", { name: "Pasaport başvurusu" });
  await user.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(button).toHaveFocus();

  await user.keyboard(" ");
  expect(
    await screen.findByRole("heading", { name: "Pasaport başvurusu" }),
  ).toBeVisible();
});

it("popover · a failed fetch shows the retry message and a retry loads the text", async () => {
  let attempts = 0;
  stubTranslationApi(() =>
    ++attempts <= 2
      ? new Response("", { status: 500 })
      : json(translationTextFixture()),
  );
  const { user } = renderPopover(translationSummaryFixture());

  await user.click(await screen.findByRole("button", { name: "Show translation" }));

  expect(
    await screen.findByText(
      "The translation could not be loaded.",
      {},
      { timeout: 4000 },
    ),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(
    await screen.findByRole("heading", { name: "Pasaport başvurusu" }),
  ).toBeVisible();
});

it("popover · absent when translation is null", async () => {
  const fetchMock = stubTranslationApi(() => json(translationTextFixture()));
  renderPopover(null);

  await Promise.resolve();

  expect(trigger()).toBeNull();
  expect(translationCalls(fetchMock)).toHaveLength(0);
});

it("popover · absent for locale de even when a summary is passed", async () => {
  renderPopover(translationSummaryFixture({ locale: "de" }));

  await Promise.resolve();

  expect(trigger()).toBeNull();
});

it("popover · very long text scrolls inside the content and does not overflow the viewport", async () => {
  stubTranslationApi(() =>
    json(translationTextFixture({ description: "Uzun ".repeat(2000) })),
  );
  const { user } = renderPopover(translationSummaryFixture());

  await user.click(await screen.findByRole("button", { name: "Show translation" }));
  const dialog = await screen.findByRole("dialog");
  const css = elementCss(dialog);

  expect(css).toMatch(/overflow-y:\s*auto/);
  expect(css).toMatch(/max-height:/);
  expect(css).toMatch(/max-width:/);
});

it("popover · the trigger is a 44 px touch target", async () => {
  renderPopover(translationSummaryFixture());

  const css = elementCss(
    await screen.findByRole("button", { name: "Show translation" }),
  );

  expect(css).toMatch(/min-width:\s*var\(--chakra-sizes-11\)/);
  expect(css).toMatch(/min-height:\s*var\(--chakra-sizes-11\)/);
});

it("popover · never requests a model: only the stored-text route is called", async () => {
  const fetchMock = stubTranslationApi(() => json(translationTextFixture()));
  const { user } = renderPopover(translationSummaryFixture());

  await user.click(await screen.findByRole("button", { name: "Show translation" }));
  await screen.findByRole("heading", { name: "Pasaport başvurusu" });

  const urls = vi.mocked(fetchMock).mock.calls.map(([input]) => String(input));
  expect(urls.filter((url) => /translation|candidates/.test(url))).toEqual([
    expect.stringContaining("/api/v1/candidates/c1/translation"),
  ]);
});
