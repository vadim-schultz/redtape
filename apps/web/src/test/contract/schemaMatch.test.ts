import { describe, expect, it } from "vitest";

import {
  diffEnum,
  diffFields,
  enumValues,
  propertyNames,
  type SchemaRegistry,
} from "./schemaMatch";

const REGISTRY: SchemaRegistry = {
  Item: {
    properties: {
      id: { type: "string" },
      status: { $ref: "#/components/schemas/Status" },
      note: { anyOf: [{ type: "string" }, { type: "null" }] },
    },
  },
  Status: { enum: ["open", "closed"] },
  Wrapped: { allOf: [{ $ref: "#/components/schemas/Item" }] },
};

describe("schemaMatch", () => {
  it("reports a missing and an extra field", () => {
    expect(diffFields(REGISTRY, "Item", ["id", "extra"])).toEqual({
      missing: ["note", "status"],
      extra: ["extra"],
    });
  });

  it("reports an enum value that is not in the web list", () => {
    expect(diffEnum(REGISTRY, "Status", ["open"])).toEqual({
      missing: ["closed"],
      extra: [],
    });
  });

  it("reports an enum value the web list has and the API lacks", () => {
    expect(
      diffEnum(REGISTRY, "Status", ["open", "closed", "archived"]),
    ).toEqual({
      missing: [],
      extra: ["archived"],
    });
  });

  it("resolves $ref and nullable anyOf to the property names", () => {
    expect(propertyNames(REGISTRY, "Item")).toEqual(["id", "note", "status"]);
  });

  it("follows allOf to the property names of the member", () => {
    expect(propertyNames(REGISTRY, "Wrapped")).toEqual([
      "id",
      "note",
      "status",
    ]);
  });

  it("returns the enum values in order", () => {
    expect(enumValues(REGISTRY, "Status")).toEqual(["open", "closed"]);
  });

  it("throws for an unknown schema name", () => {
    expect(() => propertyNames(REGISTRY, "Missing")).toThrow(
      "no component schema named Missing",
    );
  });
});
