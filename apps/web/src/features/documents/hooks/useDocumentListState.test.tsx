import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { expect, it } from "vitest";

import { useDocumentListState } from "./useDocumentListState";

function renderState(url: string) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>
  );
  return renderHook(
    () => ({ list: useDocumentListState(), location: useLocation() }),
    { wrapper },
  );
}

it("useDocumentListState · defaults omit every URL param", () => {
  const { result } = renderState("/documents");

  expect(result.current.list.state).toMatchObject({ offset: 0, limit: 20 });
  expect(result.current.list.state.search).toBeUndefined();
  expect(result.current.list.state.sortBy).toBeUndefined();
});

it("useDocumentListState · search and offset round-trip through the URL", () => {
  const { result } = renderState("/documents?q=ausweis&offset=40");

  expect(result.current.list.state).toMatchObject({
    search: "ausweis",
    offset: 40,
  });
});

it("useDocumentListState · setSearch writes q and resets the page", () => {
  const { result } = renderState("/documents?offset=40&category=a");

  act(() => result.current.list.setSearch("pass"));

  const params = new URLSearchParams(result.current.location.search);
  expect(params.get("q")).toBe("pass");
  expect(params.has("offset")).toBe(false);
  expect(params.get("category")).toBe("a");
});

it("useDocumentListState · a blank search removes q instead of writing it", () => {
  const { result } = renderState("/documents?q=pass");

  act(() => result.current.list.setSearch("   "));

  expect(result.current.location.search).toBe("");
});

it("list state · stale sort_by and sort_order URL params are ignored and dropped", () => {
  const { result } = renderState(
    "/documents?sort_by=title&sort_order=desc&q=pass",
  );

  expect(result.current.list.state.sortBy).toBeUndefined();
  expect(result.current.list.state.sortOrder).toBeUndefined();

  act(() => result.current.list.setOffset(20));

  const params = new URLSearchParams(result.current.location.search);
  expect(params.has("sort_by")).toBe(false);
  expect(params.has("sort_order")).toBe(false);
  expect(params.get("q")).toBe("pass");
  expect(params.get("offset")).toBe("20");
});

it("list state · a stale sort key the server once accepted is ignored too", () => {
  const { result } = renderState("/documents?sort_by=completeness");

  expect(result.current.list.state.sortBy).toBeUndefined();
});

it.each(["-5", "abc", "1.5", ""])(
  "useDocumentListState · offset %j in the URL is ignored",
  (offset) => {
    const { result } = renderState(`/documents?offset=${offset}`);

    expect(result.current.list.state.offset).toBe(0);
  },
);

it("useDocumentListState · setOffset moves the page and keeps the rest", () => {
  const { result } = renderState("/documents?q=pass&category=a");

  act(() => result.current.list.setOffset(20));

  const params = new URLSearchParams(result.current.location.search);
  expect(params.get("offset")).toBe("20");
  expect(params.get("q")).toBe("pass");
  expect(params.get("category")).toBe("a");
});
