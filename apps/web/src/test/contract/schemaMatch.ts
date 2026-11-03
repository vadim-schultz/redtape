// Reads just enough of an OpenAPI component schema to compare its enum values
// and property names with the web types. No validation, no dependency.

/** The parts of a JSON Schema this matcher reads. */
export interface Schema {
  type?: string | readonly string[];
  format?: string;
  title?: string;
  /** Mixed in nullable and numeric enums; the enum helpers keep strings only. */
  enum?: readonly unknown[];
  properties?: Readonly<Record<string, Schema>>;
  required?: readonly string[];
  items?: Schema;
  $ref?: string;
  allOf?: readonly Schema[];
  anyOf?: readonly Schema[];
  oneOf?: readonly Schema[];
}

/** Component schemas by name, as `components.schemas` holds them. */
export type SchemaRegistry = Readonly<Record<string, Schema>>;

export interface Difference {
  /** Present in the API schema, absent from the web side. */
  missing: string[];
  /** Present on the web side, absent from the API schema. */
  extra: string[];
}

const REF_PREFIX = "#/components/schemas/";

function lookup(registry: SchemaRegistry, name: string): Schema {
  const schema = registry[name];
  if (schema === undefined)
    throw new Error(`no component schema named ${name}`);
  return schema;
}

/** Follows `$ref` and unwraps a nullable `anyOf` (`[X, {type: "null"}]`) to `X`. */
function resolve(registry: SchemaRegistry, schema: Schema): Schema {
  if (schema.$ref !== undefined) {
    const name = schema.$ref.slice(REF_PREFIX.length);
    return resolve(registry, lookup(registry, name));
  }
  const members = schema.anyOf ?? [];
  const nonNull = members.filter((member) => member.type !== "null");
  if (members.length === 2 && nonNull.length === 1) {
    return resolve(registry, nonNull[0]);
  }
  return schema;
}

function collectProperties(
  registry: SchemaRegistry,
  schema: Schema,
  into: Set<string>,
): void {
  const resolved = resolve(registry, schema);
  for (const name of Object.keys(resolved.properties ?? {})) into.add(name);
  for (const member of resolved.allOf ?? []) {
    collectProperties(registry, member, into);
  }
}

/** The enum values a named component schema allows, in the API's order. */
export function enumValues(registry: SchemaRegistry, name: string): string[] {
  const values = resolve(registry, lookup(registry, name)).enum;
  if (values === undefined) throw new Error(`${name} is not an enum`);
  return values.filter((value): value is string => typeof value === "string");
}

/** The sorted property names of a named component schema, following `$ref` and `allOf`. */
export function propertyNames(
  registry: SchemaRegistry,
  name: string,
): string[] {
  const names = new Set<string>();
  collectProperties(registry, lookup(registry, name), names);
  return [...names].sort();
}

function diff(api: readonly string[], web: readonly string[]): Difference {
  const apiSet = new Set(api);
  const webSet = new Set(web);
  return {
    missing: [...apiSet].filter((value) => !webSet.has(value)).sort(),
    extra: [...webSet].filter((value) => !apiSet.has(value)).sort(),
  };
}

/** Compares a web field list with the property names of a named API schema. */
export function diffFields(
  registry: SchemaRegistry,
  name: string,
  webFields: readonly string[],
): Difference {
  return diff(propertyNames(registry, name), webFields);
}

/** Compares a web value list with the enum values of a named API schema. */
export function diffEnum(
  registry: SchemaRegistry,
  name: string,
  webValues: readonly string[],
): Difference {
  return diff(enumValues(registry, name), webValues);
}
