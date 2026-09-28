import { expect, it } from "vitest";

import { ApiRequestError } from "../../../services/api";
import { parseFieldErrors } from "./parseFieldErrors";

function errorWithBody(body: unknown, status = 422): ApiRequestError {
  return new ApiRequestError({
    status,
    url: "https://api.test/api/v1/suggestions",
    bodyText: JSON.stringify(body),
  });
}

it("parseFieldErrors · maps Litestar validation extras to field names", () => {
  const error = errorWithBody({
    status_code: 422,
    detail: "Validation failed",
    extra: [
      {
        key: "payload.official_url",
        message: "official_url must use http or https",
        source: "body",
      },
      {
        key: "payload.title_i18n",
        message: "title_i18n must have at least one non-blank value",
        source: "body",
      },
    ],
  });

  expect(parseFieldErrors(error)).toEqual({
    official_url: "official_url must use http or https",
    title_i18n: "title_i18n must have at least one non-blank value",
  });
});

it("parseFieldErrors · ignores extras without a key", () => {
  const error = errorWithBody({ extra: [{ message: "generic failure" }] });

  expect(parseFieldErrors(error)).toEqual({});
});

it("parseFieldErrors · returns no field errors when the body is not JSON", () => {
  const error = new ApiRequestError({
    status: 422,
    url: "https://api.test/api/v1/suggestions",
    bodyText: "not json",
  });

  expect(parseFieldErrors(error)).toEqual({});
});
