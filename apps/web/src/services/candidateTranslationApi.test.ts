import { afterEach, expect, it, vi } from "vitest";

import { json, stubTranslationApi } from "../test/candidatesApiStub";
import { translationTextFixture } from "../test/candidateFixtures";
import { fetchCandidateTranslation } from "./candidateTranslationApi";

afterEach(() => vi.unstubAllGlobals());

it("translation api · asks for the locale on the path's query and in Accept-Language", async () => {
  const fetchMock = stubTranslationApi(() => json(translationTextFixture()));

  const text = await fetchCandidateTranslation({ id: "c1", locale: "tr" });

  const [input, init] = fetchMock.mock.calls[0] as [string, RequestInit];
  expect(new URL(input).pathname).toBe("/api/v1/candidates/c1/translation");
  expect(new URL(input).searchParams.get("locale")).toBe("tr");
  expect((init.headers as Record<string, string>)["Accept-Language"]).toBe(
    "tr",
  );
  expect(text.title).toBe("Pasaport başvurusu");
});

it("translation api · rejects with the API error when the text is missing", async () => {
  stubTranslationApi(() => new Response("", { status: 404 }));

  await expect(
    fetchCandidateTranslation({ id: "c1", locale: "tr" }),
  ).rejects.toMatchObject({ status: 404 });
});

it("translation api · escapes an id that is not path safe", async () => {
  const fetchMock = stubTranslationApi(() => json(translationTextFixture()));

  await fetchCandidateTranslation({ id: "a/b", locale: "tr" }).catch(
    () => undefined,
  );

  const [input] = fetchMock.mock.calls[0] as [string];
  expect(new URL(input).pathname).toBe("/api/v1/candidates/a%2Fb/translation");
});
