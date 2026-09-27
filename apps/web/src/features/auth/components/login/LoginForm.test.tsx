import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import LoginForm from "./LoginForm";

function typeEmail(user: ReturnType<typeof renderWithProviders>["user"], value: string) {
  return user.type(screen.getByRole("textbox"), value);
}

it("LoginForm · submits the entered email to the gateway", async () => {
  const onSubmit = vi.fn();
  const { user } = renderWithProviders(
    <LoginForm onSubmit={onSubmit} isSending={false} />,
  );

  await typeEmail(user, "ada@example.com");
  await user.click(screen.getByRole("button"));

  expect(onSubmit).toHaveBeenCalledExactlyOnceWith("ada@example.com");
});

it("LoginForm · rejects an empty email without calling the gateway", async () => {
  const onSubmit = vi.fn();
  const { user } = renderWithProviders(
    <LoginForm onSubmit={onSubmit} isSending={false} />,
  );

  await user.click(screen.getByRole("button"));

  expect(onSubmit).not.toHaveBeenCalled();
});

it("LoginForm · rejects a value without an @", async () => {
  const onSubmit = vi.fn();
  const { user } = renderWithProviders(
    <LoginForm onSubmit={onSubmit} isSending={false} />,
  );

  await typeEmail(user, "not-an-email");
  await user.click(screen.getByRole("button"));

  expect(onSubmit).not.toHaveBeenCalled();
});

it("LoginForm · disables the button while sending", () => {
  renderWithProviders(<LoginForm onSubmit={vi.fn()} isSending />);

  expect(screen.getByRole("button")).toBeDisabled();
});
