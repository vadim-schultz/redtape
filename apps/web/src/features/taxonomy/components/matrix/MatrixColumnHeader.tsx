import { buildDocumentsHref } from "../../../documents/utils/buildDocumentsHref";
import type { MatrixAxisItem } from "../../types";
import HeaderLink from "./HeaderLink";

export default function MatrixColumnHeader({
  domain,
}: {
  domain: MatrixAxisItem;
}) {
  return (
    <HeaderLink
      to={buildDocumentsHref({ domain: domain.code })}
      name={domain.name}
      total={domain.total}
    />
  );
}
