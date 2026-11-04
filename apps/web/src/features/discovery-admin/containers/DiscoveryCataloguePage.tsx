import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { useListQueryState } from "../../../hooks/useListQueryState";
import CatalogueIndexPanel from "../components/CatalogueIndexPanel";
import { useDiscoveryCatalogueQuery } from "../hooks/useDiscoveryCatalogueQuery";
import { CATALOGUE_LIST_SPEC } from "../services/catalogueListQuery";

/** Imported catalogue index at ``/admin/discovery/catalogue``. */
export default function DiscoveryCataloguePage() {
  const list = useListQueryState(CATALOGUE_LIST_SPEC);
  const catalogueQuery = useDiscoveryCatalogueQuery(list.state);

  return (
    <CatalogueIndexPanel
      page={catalogueQuery.data}
      status={toQueryStatus(catalogueQuery)}
      list={list}
    />
  );
}
