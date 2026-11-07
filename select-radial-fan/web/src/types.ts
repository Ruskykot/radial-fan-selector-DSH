export type PressureType = "FULL" | "STATIC";

export interface SelectionQuery {
  q_req: number;
  p_req: number;
  pressure_type?: PressureType;
  d_reg_max?: number;
  t_air?: number;
  series?: string[];
  sizes?: number[];
  rpms?: number[];
}

export interface MotorInfo {
  name: string;
  n_kw: number;
  n_rpm: number;
  i_nom: number | null;
}

export interface CurvePoints {
  q_points: number[];
  p_points: number[];
  q_eff: number[];
  eff_points: number[];
  q_min: number;
  q_max: number;
}

export interface FanResultItem {
  model: string;
  series: string;
  size: number;
  dn: number | null;
  d_over_dn: number | null;
  max_n: number;
  dims: Record<string, number | null>;
  mass: number | null;
  executions: string[];
  noise_by_rpm: Record<string, number[]>;
  status: string;
  passed: boolean;
  d_reg_pa: number;
  eta_req: number;
  n_shaft_with_margin_w: number;
  n_shaft_kw: number;
  motor: MotorInfo | null;
  noise_body_dba: number;
  q_work: number;
  p_work: number;
  curve: CurvePoints;
}

export interface FanResultSummary {
  total: number;
  passed: number;
  best_model: string | null;
  best_d_reg_pa: number | null;
}

export interface FanResult {
  schema: string;
  query: Required<Omit<SelectionQuery, "pressure_type">> & {
    pressure_type: PressureType;
  };
  summary: FanResultSummary;
  results: FanResultItem[];
  error?: { code: string; message: string };
}
