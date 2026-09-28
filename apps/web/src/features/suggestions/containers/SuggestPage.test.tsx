import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import type { AuthSession } from "../../auth/services/authGateway";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import SuggestPage from "./SuggestPage";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "ada@example.com",
};

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

function respond(postSuggestion: () => Response | Promise<Response>) {
  fetchMock.mockImplementation(async (input: unknown, init?: RequestInit) => {
    const path = new URL(String(input)).pathname;
    const method = init?.method ?? "GET";
    if (path.endsWith("/me"))
      return new Response(
        JSON.stringify({
          id: "user-1",
          email: session.email,
          display_name: null,
          role: "user",
        }),
      );
    if (path.endsWith("/states"))
      return locationResponse([{ code: "BE", name: "Berlin" }]);
    if (path.endsWith("/districts"))
      return locationResponse([{ code: "BE-MITTE", name: "Mitte" }]);
    if (path.endsWith("/cities"))
      return locationResponse([{ code: "M1", name: "Berlin City" }]);
    if (path.endsWith("/domains")) return termsResponse([]);
    if (path.endsWith("/life-situations")) return termsResponse([]);
    if (path.endsWith("/suggestions") && method === "POST")
      return postSuggestion();
    return new Response(JSON.stringify({}));
  });
}

beforeEach(() => {
  window.localStorage.setItem("locale", "en");
  vi.stubGlobal("fetch", fetchMock);
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

async function fillAndSubmit(user: User) {
  await selectOnceEnabled(user, "State", "Berlin");
  await selectOnceEnabled(user, "District", "Mitte");
  await selectOnceEnabled(user, "City", "Berlin City");
  await user.type(screen.getByLabelText("Document title"), "Residency permit");
  await user.type(
    screen.getByLabelText("Official URL"),
    "https://example.gov/residency",
  );
  await user.click(screen.getByRole("button", { name: "Submit" }));
}

function renderPage() {
  return renderWithProviders(<SuggestPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });
}

it("SuggestPage · shows the success notice with a link to the new suggestion", async () => {
  respond(() =>
    Promise.resolve(new Response(JSON.stringify({ id: "s1" }), { status: 201 })),
  );
  const { user } = renderPage();

  await fillAndSubmit(user);

  expect(
    await screen.findByRole("link", { name: "View suggestion" }),
  ).toHaveAttribute("href", "/suggestions/s1");
});

it("SuggestPage · shows conflicts with links to documents and suggestions on 409", async () => {
  respond(() =>
    Promise.resolve(
      new Response(
        JSON.stringify({
          detail: "Duplicate suggestion",
          extra: {
            conflicts: [
              { type: "document", id: "d1" },
              { type: "suggestion", id: "sug1" },
            ],
          },
        }),
        { status: 409 },
      ),
    ),
  );
  const { user } = renderPage();

  await fillAndSubmit(user);

  expect(
    await screen.findByRole("link", { name: "View existing document" }),
  ).toHaveAttribute("href", "/documents/d1");
  expect(
    screen.getByRole("link", { name: "View existing suggestion" }),
  ).toHaveAttribute("href", "/suggestions/sug1");
});

it("SuggestPage · maps a 422 field error onto the URL field", async () => {
  respond(() =>
    Promise.resolve(
      new Response(
        JSON.stringify({
          status_code: 422,
          detail: "Validation failed",
          extra: [
            {
              key: "payload.official_url",
              message: "official_url must use http or https",
              source: "body",
            },
          ],
        }),
        { status: 422 },
      ),
    ),
  );
  const { user } = renderPage();

  await fillAndSubmit(user);

  expect(
    await screen.findByText("official_url must use http or https"),
  ).toBeInTheDocument();
});

it("SuggestPage · a network failure shows the generic error and keeps the form values", async () => {
  respond(() => {
    throw new Error("network down");
  });
  const { user } = renderPage();

  await fillAndSubmit(user);

  expect(
    await screen.findByText("Something went wrong. Please try again."),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Document title")).toHaveValue(
    "Residency permit",
  );
});
