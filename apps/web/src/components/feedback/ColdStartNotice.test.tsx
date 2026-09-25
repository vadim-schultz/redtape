import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { LocaleProvider } from "../../contexts/LocaleContext";
import ColdStartNotice from "./ColdStartNotice";
import { ChakraProvider } from "@chakra-ui/react";
import { system } from "../../theme";

beforeEach(() => {
  vi.useFakeTimers();
  window.localStorage.setItem("locale", "en");
});
afterEach(() => vi.useRealTimers());

function renderNotice(client: QueryClient) {
  return render(
    <QueryClientProvider client={client}>
      <ChakraProvider value={system}>
        <LocaleProvider>
          <ColdStartNotice />
        </LocaleProvider>
      </ChakraProvider>
    </QueryClientProvider>,
  );
}

function startSlowQuery(client: QueryClient) {
  void client.fetchQuery({
    queryKey: ["slow"],
    queryFn: () => new Promise(() => undefined),
  });
}

it("ColdStartNotice · stays hidden for quick requests", () => {
  const client = new QueryClient();
  renderNotice(client);
  act(() => startSlowQuery(client));
  act(() => vi.advanceTimersByTime(1)); // let the fetch state reach React

  act(() => vi.advanceTimersByTime(3_000));

  expect(screen.queryByText("Waking up the server")).not.toBeInTheDocument();
});

it("ColdStartNotice · appears once a request has been pending for a few seconds", () => {
  const client = new QueryClient();
  renderNotice(client);
  act(() => startSlowQuery(client));
  act(() => vi.advanceTimersByTime(1)); // let the fetch state reach React

  act(() => vi.advanceTimersByTime(4_100));

  expect(screen.getByText("Waking up the server")).toBeInTheDocument();
});

it("ColdStartNotice · is not shown when nothing is loading", () => {
  renderNotice(new QueryClient());

  act(() => vi.advanceTimersByTime(10_000));

  expect(screen.queryByText("Waking up the server")).not.toBeInTheDocument();
});
