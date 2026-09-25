import { useLocale } from "../../../../contexts/LocaleContext";
import { buildDocumentsHref } from "../../../documents/utils/buildDocumentsHref";
import HeaderLink from "./HeaderLink";

export default function MatrixCorner({ total }: { total: number }) {
  const { t } = useLocale();

  return (
    <HeaderLink
      to={buildDocumentsHref({})}
      name={t("matrix.all_documents")}
      total={total}
    />
  );
}
