import { describe, expect, it } from "vitest";

import type { DocumentBlock } from "../../../../types/documentTranslation";
import { groupBlocks, langOf } from "./blockGroups";

describe("block groups", () => {
  it("joins consecutive list items into one group and keeps other blocks in order", () => {
    const blocks: DocumentBlock[] = [
      { kind: "h2", text: "Heading", untranslated: false },
      { kind: "li", text: "One", untranslated: false },
      { kind: "li", text: "Two", untranslated: false },
      { kind: "p", text: "Between", untranslated: false },
      { kind: "li", text: "Three", untranslated: false },
    ];

    expect(groupBlocks(blocks).map((group) => group.type)).toEqual([
      "block",
      "list",
      "block",
      "list",
    ]);
    expect(groupBlocks(blocks)[1]).toEqual({
      type: "list",
      items: [blocks[1], blocks[2]],
    });
  });

  it("drops a block whose kind is unknown", () => {
    const unknown = {
      kind: "figure",
      text: "Caption",
      untranslated: false,
    } as unknown as DocumentBlock;

    expect(
      groupBlocks([unknown, { kind: "p", text: "Kept", untranslated: false }]),
    ).toEqual([
      {
        type: "block",
        block: { kind: "p", text: "Kept", untranslated: false },
      },
    ]);
  });

  it("drops a kind that only exists on the prototype chain", () => {
    const sneaky = {
      kind: "constructor",
      text: "x",
      untranslated: false,
    } as unknown as DocumentBlock;

    expect(groupBlocks([sneaky])).toEqual([]);
  });

  it("labels an untranslated block de and leaves a translated one without a lang", () => {
    expect(langOf({ untranslated: true })).toBe("de");
    expect(langOf({ untranslated: false })).toBeUndefined();
  });
});
