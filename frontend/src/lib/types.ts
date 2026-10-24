export type Role = "admin" | "recepcion" | "tecnico";

export interface User {
  id: number;
  username: string;
  name: string;
  role: Role;
  technician_id: number | null;
  technician: string | null;
  active: number | boolean;
}

export type OrderStatus = "recibida" | "en proceso" | "terminada" | "entregada";

export interface Service {
  id: number;
  code: string;
  name: string;
  category: string;
  observed_avg_min: number;
  rating_factor: number;
  allowance_pct: number;
  normal_min: number;
  standard_min: number;
  std_hours: number;
  parts_cost: number;
  keywords: string;
  steps: string[];
}

export interface OrderRow {
  id: number;
  folio: string;
  status: OrderStatus;
  customer: string;
  phone: string;
  vehicle: string;
  technician: string;
  technician_id: number;
  bay: string;
  bay_id: number;
  created_at: string;
  scheduled_date: string;
  due_date: string;
  std_hours: number;
  actual_hours: number | null;
  total: number;
  vencida?: boolean;
}

export interface QuoteLine {
  code: string;
  name: string;
  qty: number;
  std_hours: number;
  labor: number;
  parts: number;
  subtotal: number;
}

export interface Quote {
  horas_estandar: number;
  mano_de_obra: number;
  refacciones: number;
  margen: number;
  subtotal: number;
  iva: number;
  total: number;
  labor_rate: number;
  margin_pct: number;
  iva_rate: number;
  lines: QuoteLine[];
  formula: string;
}

export interface Timer {
  hours: number;
  running: boolean;
  running_since: string | null;
}

export interface Technician {
  id: number;
  name: string;
  specialty: string;
}

export interface Bay {
  id: number;
  name: string;
}

export interface Settings {
  labor_rate: number;
  margin_pct: number;
  efficiency_goal: number;
  service_level: number;
}
