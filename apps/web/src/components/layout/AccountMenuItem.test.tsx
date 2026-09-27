import { Menu, Portal } from "@chakra-ui/react";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../features/auth/services/fakeAuthGateway";
import type { AuthSession } from "../../features/auth/services/authGateway";
import AccountMenuItem from "./AccountMenuItem";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "ada@example.com",
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubFetch(role?: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const url = String(input);
      if (url.includes("/api/v1/me") && role) {
        return new Response(
          JSON.stringify({
            id: "user-1",
            email: session.email,
            display_name: null,
            role,
          }),
        );
      }
      return new Response("", { status: 503 });
    }),
  );
}

function renderItem(authGateway: ReturnType<typeof createFakeAuthGateway>) {
  return renderWithProviders(
    <Menu.Root defaultOpen>
      <Portal>
        <Menu.Positioner>
          <Menu.Content>
            <AccountMenuItem />
          </Menu.Content>
        </Menu.Positioner>
      </Portal>
    </Menu.Root>,
    { authGateway },
  );
}

it("AccountMenuItem · anonymous shows Sign in linking to /login", async () => {
  stubFetch();
  renderItem(createFakeAuthGateway({ session: null }));

  expect(
    await screen.findByRole("menuitem", { name: "Sign in" }),
  ).toHaveAttribute("href", "/login");
});

it("AccountMenuItem · authenticated shows the email and Sign out", async () => {
  stubFetch("user");
  renderItem(createFakeAuthGateway({ session }));

  expect(await screen.findByText(session.email)).toBeInTheDocument();
  expect(
    screen.getByRole("menuitem", { name: "Sign out" }),
  ).toBeInTheDocument();
});

it("AccountMenuItem · Sign out calls the gateway", async () => {
  stubFetch("user");
  const gateway = createFakeAuthGateway({ session });
  const signOutSpy = vi.spyOn(gateway, "signOut");
  const { user } = renderItem(gateway);

  await user.click(await screen.findByRole("menuitem", { name: "Sign out" }));

  await waitFor(() => expect(signOutSpy).toHaveBeenCalled());
});

it("AccountMenuItem · renders nothing when unconfigured", async () => {
  stubFetch();
  renderItem(createFakeAuthGateway({ configured: false }));

  await waitFor(() =>
    expect(screen.queryByRole("menuitem")).not.toBeInTheDocument(),
  );
});
