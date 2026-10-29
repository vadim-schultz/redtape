import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import type { DiscoveryArtifact } from "../../types";
import { formatBytes } from "../../utils/formatBytes";
import { formatDate } from "../../utils/formatDate";
import { hostOf } from "../../utils/hostOf";
import SnapshotDownloadCell from "./cells/SnapshotDownloadCell";
import { headerLabels, type ColumnContext } from "./columnContext";

/** Stored pages are read-only evidence: no column declares a sort or filter. */
export type SnapshotColumn = DataTableColumn<DiscoveryArtifact, never, never>;

/** Columns of the stored pages: size, fetch date, final host and a download link; content is never rendered. */
export function snapshotColumns(context: ColumnContext): SnapshotColumn[] {
  const { locale } = context;
  const header = headerLabels(context, "discovery_admin.artifacts");
  return [
    {
      key: "size",
      header: header("size"),
      render: (a) => formatBytes(a.byte_size, locale),
    },
    {
      key: "fetched",
      header: header("fetched"),
      render: (a) => formatDate(a.fetched_at, locale),
    },
    {
      key: "host",
      header: header("host"),
      render: (a) => hostOf(a.final_url ?? a.source_url),
    },
    {
      key: "download",
      header: header("download"),
      render: (a) => <SnapshotDownloadCell artifact={a} />,
    },
  ];
}
