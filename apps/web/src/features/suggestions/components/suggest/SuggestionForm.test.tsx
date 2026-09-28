import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import SuggestionForm from "./SuggestionForm";

const fetchMock = vi.fn();

function locationResponse(items: { code: string; name: string }[]) {
  return new Response(JSON.stringify({ items }));
}

function termsResponse(codes: string[]) {
  return new Response(
    JSON.stringify(
      codes.map((code) => ({
        code,
        name: code.toUpperCase(),
        description: "",
        icon: null,
      })),
    ),
  );
}

function respond() {
  fetchMock.mockImplementation(async (input: unknown) => {
    const path = new URL(String(input)).pathname;
    if (path.endsWith("/states"))
      return locationResponse([{ code: "BE", name: "Berlin" }]);
    if (path.endsWith("/districts"))
      return locationResponse([{ code: "BE-MITTE", name: "Mitte" }]);
    if (path.endsWith("/cities"))
      return locationResponse([{ code: "M1", name: "Berlin City" }]);
    if (path.endsWith("/domains")) return termsResponse(["housing"]);
    if (path.endsWith("/life-situations")) return termsResponse(["moving"]);
    return new Response(JSON.stringify({}));
  });
}

beforeEach(() => {
  window.localStorage.setItem("locale", "en");
  vi.stubGlobal("fetch", fetchMock);
  respond();
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

type User = ReturnType<typeof renderWithProviders>["user"];

async function selectOnceEnabled(user: User, name: string, option: string) {
  const trigger = screen.getByRole("combobox", { name });
  await waitFor(() => expect(trigger).toBeEnabled());
  await user.click(trigger);
  await user.click(await screen.findByRole("option", { name: option }));
  // Ark UI's Select asynchronously restores focus to its trigger on close;
  // wait for that to settle so it can't steal focus back mid-typing later.
  await waitFor(() => expect(trigger).toHaveFocus());
}

async function selectMunicipality(user: User) {
  await selectOnceEnabled(user, "State", "Berlin");
  await selectOnceEnabled(user, "District", "Mitte");
  await selectOnceEnabled(user, "City", "Berlin City");
}

function renderForm(isSending = false) {
  const onSubmit = vi.fn();
  const view = renderWithProviders(
    <SuggestionForm onSubmit={onSubmit} isSending={isSending} />,
  );
  return { onSubmit, ...view };
}

async function fillTitleAndUrl(user: User, url = "https://example.gov/residency") {
  await user.type(screen.getByLabelText("Document title"), "Residency permit");
  await user.type(screen.getByLabelText("Official URL"), url);
}

it("SuggestionForm · submits municipality_code, title under the current locale and URL", async () => {
  const { onSubmit, user } = renderForm();

  await selectMunicipality(user);
  await fillTitleAndUrl(user);
  await user.click(screen.getByRole("button", { name: "Submit" }));

  expect(onSubmit).toHaveBeenCalledExactlyOnceWith({
    municipality_code: "M1",
    payload: {
      title_i18n: { en: "Residency permit" },
      official_url: "https://example.gov/residency",
      domain_codes: [],
      situation_codes: [],
    },
  });
});

it("SuggestionForm · blocks submit without a municipality", async () => {
  const { onSubmit, user } = renderForm();

  await fillTitleAndUrl(user);
  await user.click(screen.getByRole("button", { name: "Submit" }));

  expect(onSubmit).not.toHaveBeenCalled();
});

it("SuggestionForm · blocks a blank title", async () => {
  const { onSubmit, user } = renderForm();

  await selectMunicipality(user);
  await user.type(
    screen.getByLabelText("Official URL"),
    "https://example.gov/residency",
  );
  await user.click(screen.getByRole("button", { name: "Submit" }));

  expect(onSubmit).not.toHaveBeenCalled();
});

it("SuggestionForm · blocks a URL that is not http or https", async () => {
  const { onSubmit, user } = renderForm();

  await selectMunicipality(user);
  await fillTitleAndUrl(user, "ftp://example.gov/residency");
  await user.click(screen.getByRole("button", { name: "Submit" }));

  expect(onSubmit).not.toHaveBeenCalled();
});

it("SuggestionForm · includes selected domain and situation codes", async () => {
  const { onSubmit, user } = renderForm();

  await selectMunicipality(user);
  await fillTitleAndUrl(user);
  await user.click(await screen.findByRole("button", { name: "HOUSING" }));
  await user.click(screen.getByRole("button", { name: "MOVING" }));
  await user.click(screen.getByRole("button", { name: "Submit" }));

  expect(onSubmit).toHaveBeenCalledExactlyOnceWith(
    expect.objectContaining({
      payload: expect.objectContaining({
        domain_codes: ["housing"],
        situation_codes: ["moving"],
      }),
    }),
  );
});

it("SuggestionForm · disables the submit button while sending", () => {
  renderForm(true);

  expect(screen.getByRole("button")).toBeDisabled();
});
