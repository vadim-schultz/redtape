import CatalogueIndexPanel from "../components/CatalogueIndexPanel";
import { useCatalogueListState } from "../hooks/useCatalogueListState";
import { useCatalogueState } from "../hooks/useCatalogueState";

/** Imported catalogue index at ``/admin/discovery/catalogue``. */
export default function DiscoveryCataloguePage() {
  const list = useCatalogueListState();
  const panel = useCatalogueState(list.state);

  return <CatalogueIndexPanel panel={panel} list={list} />;
}
