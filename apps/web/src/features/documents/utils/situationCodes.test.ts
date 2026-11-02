import { expect, it } from "vitest";

import type { GroupedTerm } from "../../taxonomy/types";
import { situationCodes } from "./situationCodes";

function situation(code: string, group_code: string): GroupedTerm {
  return { code, name: code, description: "", icon: null, group_code };
}

const situations = [
  situation("moving", "home"),
  situation("renting", "home"),
  situation("new-job", "work"),
];

it("situationCodes · a group expands to exactly its situations", () => {
  const codes = situationCodes(
    { groups: ["home"], situations: [] },
    situations,
  );

  expect(codes).toEqual(["moving", "renting"]);
});

it("situationCodes · a group plus an unrelated situation unions without duplicates", () => {
  const codes = situationCodes(
    { groups: ["home"], situations: ["new-job", "moving"] },
    situations,
  );

  expect([...codes].sort()).toEqual(["moving", "new-job", "renting"]);
});

it("situationCodes · unknown groups and unloaded situations contribute nothing", () => {
  const unknown = situationCodes(
    { groups: ["nope"], situations: [] },
    situations,
  );
  const unloaded = situationCodes({ groups: ["home"], situations: [] }, []);

  expect(unknown).toEqual([]);
  expect(unloaded).toEqual([]);
});

it("situationCodes · no selection sends no codes", () => {
  expect(situationCodes({ groups: [], situations: [] }, situations)).toEqual(
    [],
  );
});
