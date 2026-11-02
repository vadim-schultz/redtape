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

it("useDocumentListState · defaults omit every URL param and sort by confidence", () => {
  const { result } = renderState("/documents");

  expect(result.current.list.state).toMatchObject({ offset: 0, limit: 20 });
  expect(result.current.list.state.search).toBeUndefined();
  expect(result.current.list.state.sortBy).toBeUndefined();
  expect(result.current.list.sort).toEqual({
    sortBy: "confidence",
    sortOrder: "desc",
  });
});

it("useDocumentListState · values round-trip through the URL", () => {
  const { result } = renderState(
    "/documents?q=ausweis&sort_by=title&sort_order=desc&offset=40",
  );

  expect(result.current.list.state).toMatchObject({
    search: "ausweis",
    sortBy: "title",
    sortOrder: "desc",
    offset: 40,
  });
  expect(result.current.list.sort).toEqual({
    sortBy: "title",
    sortOrder: "desc",
  });
});

it("useDocumentListState · setSearch writes q and resets the page", () => {
  const { result } = renderState("/documents?offset=40&domain=a");

  act(() => result.current.list.setSearch("pass"));

  const params = new URLSearchParams(result.current.location.search);
  expect(params.get("q")).toBe("pass");
  expect(params.has("offset")).toBe(false);
  expect(params.get("domain")).toBe("a");
});

it("useDocumentListState · a blank search removes q instead of writing it", () => {
  const { result } = renderState("/documents?q=pass");

  act(() => result.current.list.setSearch("   "));

  expect(result.current.location.search).toBe("");
});

it("useDocumentListState · choosing the default sort keeps it out of the URL", () => {
  const { result } = renderState("/documents?sort_by=title&sort_order=asc");

  act(() =>
    result.current.list.setSort({ sortBy: "confidence", sortOrder: "desc" }),
  );

  expect(result.current.location.search).toBe("");
});

it("useDocumentListState · a non-default sort is written and resets the page", () => {
  const { result } = renderState("/documents?offset=20");

  act(() =>
    result.current.list.setSort({ sortBy: "created_at", sortOrder: "asc" }),
  );

  const params = new URLSearchParams(result.current.location.search);
  expect(params.get("sort_by")).toBe("created_at");
  expect(params.get("sort_order")).toBe("asc");
  expect(params.has("offset")).toBe(false);
});

it("useDocumentListState · an unknown sort key in the URL falls back to the default", () => {
  const { result } = renderState("/documents?sort_by=completeness");

  expect(result.current.list.state.sortBy).toBeUndefined();
  expect(result.current.list.sort).toEqual({
    sortBy: "confidence",
    sortOrder: "desc",
  });
});

it.each(["-5", "abc", "1.5", ""])(
  "useDocumentListState · offset %j in the URL is ignored",
  (offset) => {
    const { result } = renderState(`/documents?offset=${offset}`);

    expect(result.current.list.state.offset).toBe(0);
  },
);

it("useDocumentListState · setOffset moves the page and keeps the rest", () => {
  const { result } = renderState("/documents?q=pass&domain=a");

  act(() => result.current.list.setOffset(20));

  const params = new URLSearchParams(result.current.location.search);
  expect(params.get("offset")).toBe("20");
  expect(params.get("q")).toBe("pass");
  expect(params.get("domain")).toBe("a");
});
