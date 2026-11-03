import schemaJson from "./openapi.schemas.json";
import type { SchemaRegistry } from "./schemaMatch";

/** The API's component schemas, as committed in openapi.schemas.json (regenerate with apps/api/scripts/export_openapi.py). */
export const API_SCHEMAS: SchemaRegistry = schemaJson;
