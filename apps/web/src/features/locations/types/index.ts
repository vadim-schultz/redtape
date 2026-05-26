export type LocationKind = "COUNTRY" | "REGION" | "MUNICIPALITY" | "LOCALITY";

export type LocationNode = {
  code: string;
  name: string;
  kind: LocationKind;
  openplz_type?: string | null;
};

export type LocationListResponse = {
  items: LocationNode[];
};
