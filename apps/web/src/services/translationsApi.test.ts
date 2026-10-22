import { afterEach, expect, it, vi } from "vitest";

import { fetchTranslations } from "./translationsApi";

const signal = new AbortController().signal;

function stubFetch(response: Promise<Response>) {
  const fetchMock = vi.fn(() => response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

it("fetchTranslations · returns the parsed bundle for the locale", async () => {
  const fetchMock = stubFetch(
    Promise.resolve(new Response(JSON.stringify({ translations: { a: "A" } }))),
  );

  await expect(fetchTranslations("de", signal)).resolves.toEqual({ a: "A" });

  const [url, init] = fetchMock.mock.calls[0] as unknown as [
    string,
    RequestInit,
  ];
  expect(new URL(url).searchParams.get("locale")).toBe("de");
  expect(init.headers).toEqual({ "Accept-Language": "de" });
});

it("fetchTranslations · returns an empty bundle when the body has none", async () => {
  stubFetch(Promise.resolve(new Response("{}")));

  await expect(fetchTranslations("en", signal)).resolves.toEqual({});
});

it("fetchTranslations · rejects on a non-OK response", async () => {
  stubFetch(Promise.resolve(new Response("boom", { status: 500 })));

  await expect(fetchTranslations("en", signal)).rejects.toThrow(
    "Translations request failed: 500",
  );
});

it("fetchTranslations · rejects on a network failure", async () => {
  stubFetch(Promise.reject(new Error("offline")));

  await expect(fetchTranslations("en", signal)).rejects.toThrow("offline");
});
