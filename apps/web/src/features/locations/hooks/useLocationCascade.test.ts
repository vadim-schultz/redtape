import { act, renderHook } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { useLocationCascade } from "./useLocationCascade";

const onMunicipalityChange = vi.fn();

beforeEach(() => onMunicipalityChange.mockClear());

function setup() {
  return renderHook(() => useLocationCascade({ onMunicipalityChange }));
}

it("useLocationCascade · starts empty and not resettable", () => {
  const { result } = setup();

  expect(result.current.stateCode).toBe("");
  expect(result.current.canReset).toBe(false);
});

it("useLocationCascade · choosing a state clears deeper levels and emits null", () => {
  const { result } = setup();

  act(() => result.current.selectDistrict("D1"));
  act(() => result.current.selectMunicipality("M1"));
  onMunicipalityChange.mockClear();
  act(() => result.current.selectState("S1"));

  expect(result.current.stateCode).toBe("S1");
  expect(result.current.districtCode).toBe("");
  expect(result.current.municipalityCode).toBe("");
  expect(onMunicipalityChange).toHaveBeenCalledWith(null);
});

it("useLocationCascade · choosing a district clears the city and emits null", () => {
  const { result } = setup();

  act(() => result.current.selectMunicipality("M1"));
  onMunicipalityChange.mockClear();
  act(() => result.current.selectDistrict("D1"));

  expect(result.current.municipalityCode).toBe("");
  expect(onMunicipalityChange).toHaveBeenCalledWith(null);
});

it("useLocationCascade · choosing a city emits its code", () => {
  const { result } = setup();

  act(() => result.current.selectMunicipality("M1"));

  expect(onMunicipalityChange).toHaveBeenCalledWith("M1");
});

it("useLocationCascade · reset clears everything and emits null", () => {
  const { result } = setup();

  act(() => result.current.selectState("S1"));
  expect(result.current.canReset).toBe(true);
  onMunicipalityChange.mockClear();
  act(() => result.current.reset());

  expect(result.current.stateCode).toBe("");
  expect(result.current.canReset).toBe(false);
  expect(onMunicipalityChange).toHaveBeenCalledWith(null);
});
