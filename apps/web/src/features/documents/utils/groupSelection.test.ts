import { expect, it } from "vitest";

import type { GroupedTerm } from "../../taxonomy/types";
import {
  toggleGroupSelection,
  toggleSituationSelection,
} from "./groupSelection";

function situation(code: string, group_code: string): GroupedTerm {
  return { code, name: code, description: "", icon: null, group_code };
}

const situations = [
  situation("moving", "home"),
  situation("renting", "home"),
  situation("new-job", "work"),
];

it("groupSelection · selecting a group removes its situations and keeps the others", () => {
  const next = toggleGroupSelection(
    { groups: [], situations: ["moving", "new-job"] },
    "home",
    situations,
  );

  expect(next).toEqual({ groups: ["home"], situations: ["new-job"] });
});

it("groupSelection · selecting a situation removes its group", () => {
  const next = toggleSituationSelection(
    { groups: ["home"], situations: [] },
    "moving",
    situations,
  );

  expect(next).toEqual({ groups: [], situations: ["moving"] });
});

it("groupSelection · situations of two groups keep both", () => {
  const first = toggleSituationSelection(
    { groups: [], situations: [] },
    "moving",
    situations,
  );
  const both = toggleSituationSelection(first, "new-job", situations);

  expect(both).toEqual({ groups: [], situations: ["moving", "new-job"] });
});

it("groupSelection · deselecting works both ways", () => {
  const withoutGroup = toggleGroupSelection(
    { groups: ["home"], situations: [] },
    "home",
    situations,
  );
  const withoutSituation = toggleSituationSelection(
    { groups: [], situations: ["moving"] },
    "moving",
    situations,
  );

  expect(withoutGroup).toEqual({ groups: [], situations: [] });
  expect(withoutSituation).toEqual({ groups: [], situations: [] });
});

it("groupSelection · a sub-situation of a selected group leaves exactly one state", () => {
  const next = toggleSituationSelection(
    { groups: ["home"], situations: [] },
    "renting",
    situations,
  );

  expect(next.groups).toEqual([]);
  expect(next.situations).toEqual(["renting"]);
});

it("groupSelection · unknown codes and an empty taxonomy are tolerated", () => {
  const unknownSituation = toggleSituationSelection(
    { groups: ["home"], situations: [] },
    "ghost",
    situations,
  );
  const unloaded = toggleGroupSelection(
    { groups: [], situations: ["moving"] },
    "home",
    [],
  );

  expect(unknownSituation).toEqual({ groups: ["home"], situations: ["ghost"] });
  expect(unloaded).toEqual({ groups: ["home"], situations: ["moving"] });
});
