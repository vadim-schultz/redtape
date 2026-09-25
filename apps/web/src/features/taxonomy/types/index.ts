export type Term = {
  code: string;
  name: string;
  description: string;
  icon: string | null;
};

export type MatrixCell = {
  domain: string;
  situation: string;
  count: number;
};

export type AxisTotal = {
  code: string;
  count: number;
};

export type MatrixResponse = {
  total: number;
  cells: MatrixCell[];
  situations: AxisTotal[];
  domains: AxisTotal[];
};
