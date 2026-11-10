import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fallbackBundle } from "../i18n/fallback";
import { loadBundle } from "../i18n";
import { useLocaleBundle } from "./useLocaleBundle";

vi.mock("../i18n", () => ({ loadBundle: vi.fn() }));

const TR = { "common.menu": "Menü (tr)" };
const RU = { "common.menu": "Меню" };

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => (resolve = done));
  return { promise, resolve };
}

beforeEach(() => {
  vi.mocked(loadBundle).mockReset();
  vi.mocked(loadBundle).mockImplementation(async (locale) =>
    fallbackBundle(locale),
  );
});

describe("useLocaleBundle", () => {
  it("shows the bundled en strings first, then the lazily loaded locale", async () => {
    const lazy = deferred<Record<string, string>>();
    vi.mocked(loadBundle).mockReturnValueOnce(lazy.promise);

    const { result } = renderHook(() => useLocaleBundle("tr"));
    expect(result.current).toEqual(fallbackBundle("en"));

    await act(async () => lazy.resolve(TR));
    expect(result.current).toEqual(TR);
  });

  it("ignores a late bundle for a locale the reader already left", async () => {
    const slow = deferred<Record<string, string>>();
    vi.mocked(loadBundle)
      .mockReturnValueOnce(slow.promise)
      .mockResolvedValueOnce(RU);

    const { result, rerender } = renderHook(
      ({ locale }) => useLocaleBundle(locale),
      { initialProps: { locale: "tr" } },
    );
    rerender({ locale: "ru" });
    await waitFor(() => expect(result.current).toEqual(RU));

    await act(async () => slow.resolve(TR));
    expect(result.current).toEqual(RU);
  });
});
