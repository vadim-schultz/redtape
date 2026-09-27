import { Route, Routes, type InitialEntry } from "react-router-dom";
import { screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../services/fakeAuthGateway";
import type { AuthSession } from "../services/authGateway";
import LoginPage from "./LoginPage";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "ada@example.com",
};

function renderLoginPage(
  authGateway: ReturnType<typeof createFakeAuthGateway>,
  initialEntries: InitialEntry[] = ["/login"],
) {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/documents" element={<div>documents-landing</div>} />
      <Route path="/documents/42" element={<div>doc-42</div>} />
    </Routes>,
    { initialEntries, authGateway },
  );
}

async function submitEmail(
  user: ReturnType<typeof renderWithProviders>["user"],
  email = "ada@example.com",
) {
  await user.type(screen.getByRole("textbox"), email);
  await user.click(screen.getByRole("button"));
}

it("LoginPage · shows the sent notice after a successful request", async () => {
  const signInWithEmail = vi.fn(async () => {});
  const gateway = createFakeAuthGateway({ session: null, signInWithEmail });
  const { user } = renderLoginPage(gateway);

  await submitEmail(user);

  expect(await screen.findByText(/check your inbox/i)).toBeInTheDocument();
  expect(signInWithEmail).toHaveBeenCalledExactlyOnceWith("ada@example.com");
});

it("LoginPage · shows the error notice when the gateway fails", async () => {
  const gateway = createFakeAuthGateway({
    session: null,
    signInWithEmail: async () => {
      throw new Error("network down");
    },
  });
  const { user } = renderLoginPage(gateway);

  await submitEmail(user);

  expect(
    await screen.findByText(/something went wrong/i),
  ).toBeInTheDocument();
  expect(screen.getByRole("textbox")).toBeEnabled();
  expect(screen.getByRole("button")).toBeEnabled();
});

it("LoginPage · shows the unavailable message when auth is unconfigured", async () => {
  const gateway = createFakeAuthGateway({ configured: false });
  renderLoginPage(gateway);

  expect(
    await screen.findByText(/sign-in is not available/i),
  ).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});

it("LoginPage · redirects to the originating page once authenticated", async () => {
  const gateway = createFakeAuthGateway({ session });
  renderLoginPage(gateway, [
    { pathname: "/login", state: { from: { pathname: "/documents/42" } } },
  ]);

  await waitFor(() =>
    expect(screen.getByText("doc-42")).toBeInTheDocument(),
  );
});

it("LoginPage · redirects to /documents when there is no origin", async () => {
  const gateway = createFakeAuthGateway({ session });
  renderLoginPage(gateway);

  await waitFor(() =>
    expect(screen.getByText("documents-landing")).toBeInTheDocument(),
  );
});
