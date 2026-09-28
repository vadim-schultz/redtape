import type { ApiRequestError } from "../../../services/api";

export type FieldErrors = Record<string, string>;

type ValidationExtra = { key?: string; message: string };

function fieldName(key: string): string {
  return key.split(".").pop() as string;
}

/** Maps a Litestar validation body's `extra` entries to `{ field: message }`. */
export function parseFieldErrors(error: ApiRequestError): FieldErrors {
  let body: { extra?: ValidationExtra[] };
  try {
    body = JSON.parse(error.bodyText) as { extra?: ValidationExtra[] };
  } catch {
    return {};
  }

  return (body.extra ?? []).reduce<FieldErrors>((errors, item) => {
    if (!item.key) return errors;
    return { ...errors, [fieldName(item.key)]: item.message };
  }, {});
}
