import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../../features/auth/services/fakeAuthGateway";
import type { AuthSession } from "../../../features/auth/services/authGateway";
import ProfileMenuRow from "./ProfileMenuRow";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "ada@example.com",
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function renderRow(authGateway: ReturnType<typeof createFakeAuthGateway>) {
  return renderWithProviders(<ProfileMenuRow />, { authGateway });
}

it("ProfileMenuRow · anonymous shows sign-in icons linking to /login", async () => {
  renderRow(createFakeAuthGateway({ session: null }));

  expect(
    await screen.findByRole("link", { name: "Sign in with email" }),
  ).toHaveAttribute("href", "/login");
  expect(
    screen.getByRole("link", { name: "Sign in with Google" }),
  ).toHaveAttribute("href", "/login");
});

it("ProfileMenuRow · authenticated shows user icon and Sign out", async () => {
  const { container } = renderRow(createFakeAuthGateway({ session }));

  await screen.findByRole("button", { name: "Sign out" });
  await waitFor(() =>
    expect(container.querySelector("[data-icon='user']")).toBeTruthy(),
  );
});

it("ProfileMenuRow · Sign out calls the gateway", async () => {
  const gateway = createFakeAuthGateway({ session });
  const signOutSpy = vi.spyOn(gateway, "signOut");
  const { user } = renderRow(gateway);

  await user.click(await screen.findByRole("button", { name: "Sign out" }));

  await waitFor(() => expect(signOutSpy).toHaveBeenCalled());
});

it("ProfileMenuRow · renders nothing when unconfigured", async () => {
  renderRow(createFakeAuthGateway({ configured: false }));

  await waitFor(() =>
    expect(screen.queryByTestId("key-value-row")).not.toBeInTheDocument(),
  );
});
