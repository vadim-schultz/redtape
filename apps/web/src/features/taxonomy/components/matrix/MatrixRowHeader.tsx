import { buildDocumentsHref } from "../../../documents/utils/buildDocumentsHref";
import type { MatrixAxisItem } from "../../types";
import HeaderLink from "./HeaderLink";

export default function MatrixRowHeader({
  situation,
}: {
  situation: MatrixAxisItem;
}) {
  return (
    <HeaderLink
      to={buildDocumentsHref({ situation: situation.code })}
      name={situation.name}
      total={situation.total}
    />
  );
}
