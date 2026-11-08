export interface User {
  id: string;
  username: string;
  email: string;
  role: "customer" | "admin";
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  brand: string;
  category: string;
  variant?: string;
  unit_of_measurement: string;
  price_aed: number;
  stock_quantity: number;
  is_available: boolean;
  image_url?: string;
  created_at?: string;
}

export interface ProductSearchResponse {
  products: Product[];
  total?: number;
  total_count?: number;
}

export interface CartItem {
  id: string;
  cart_id: string;
  product_id: string;
  quantity: number;
  unit_price_aed: number;
  subtotal_aed: number;
  added_at: string;
  product?: Product;
}

export interface CartResponse {
  id: string;
  user_id: string;
  session_id: string;
  items: CartItem[];
  subtotal_aed: number;
  vat_aed: number;
  grand_total_aed: number;
  item_count: number;
  created_at: string;
  updated_at: string;
  note?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  message_type?: "text" | "product_options" | "basket_update" | "error";
  products_to_select?: Product[];
  action_taken?: string;
}

export interface ChatResponse {
  message: string;
  action_taken?: string | null;
  products_to_select?: Product[] | null;
  basket_updated: boolean;
  cart?: CartResponse | null;
  audio_base64?: string | null;
}

export interface AgentRegistry {
  id: string;
  agent_id: string;
  name: string;
  description: string;
  role: string;
  department: string;
  model_provider: string;
  model_version: string;
  owner_tenant: string;
  status: "active" | "inactive";
  allowed_tools: string[];
  created_at: string;
  total_requests?: number;
  failure_count?: number;
}

export interface ApprovalRequest {
  id: string;
  trace_id: string;
  agent_id: string;
  user_id?: string | null;
  session_id?: string | null;
  tool_name: string;
  action: string;
  parameters: Record<string, any>;
  status: "pending" | "approved" | "rejected";
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  reason?: string | null;
  created_at: string;
  resolved_at?: string | null;
  resolved_by?: string | null;
  resolution_notes?: string | null;
}

export interface ToolRegistry {
  id: string;
  tool_name: string;
  description: string;
  input_schema: Record<string, any>;
  permission_level: "public" | "restricted";
  is_active: boolean;
  created_at: string;
}

export interface AuditLog {
  id: string;
  event_id: string;
  timestamp: string;
  trace_id: string;
  agent_id: string;
  user_id: string;
  session_id: string;
  tool_name: string;
  action: string;
  target_resource: string;
  governance_decision: "allowed" | "denied";
  execution_status: "success" | "failed" | "pending";
  denial_reason?: string | null;
  execution_duration_ms: number;
  metadata?: Record<string, any> | null;
}

export interface DashboardMetrics {
  total_actions: number;
  allowed_actions: number;
  denied_actions: number;
  failed_actions: number;
  success_rate: number;
  avg_duration_ms: number;

  // Separated & Precise Observability Metrics
  total_agent_requests: number;
  total_tool_calls: number;
  policy_allow_rate: number;
  policy_denial_rate: number;
  approval_required_actions: number;
  tool_execution_success_rate: number;
  tool_execution_failure_rate: number;
  avg_ai_inference_ms: number;
  avg_tool_execution_ms: number;
  avg_e2e_latency_ms: number;

  tool_usage_breakdown: Record<string, number>;
  agent_activity: Record<string, number>;
  recent_logs: AuditLog[];
  jaeger_ui_url?: string | null;
}

export interface TraceSpan {
  id?: string;
  trace_id: string;
  span_id: string;
  parent_span_id?: string | null;
  name: string;
  service_name: string;
  start_time: string;
  end_time: string;
  duration_ms: number;
  status: "ok" | "error";
  attributes: Record<string, any>;
  events?: any[];
}

export interface TraceSummary {
  trace_id: string;
  start_time: string;
  total_duration_ms: number;
  status: "ok" | "error";
  root_action: string;
  user_message?: string | null;
  spans_count: number;
  jaeger_url?: string | null;
}

export interface TraceJourneyResponse {
  trace_id: string;
  start_time: string;
  total_duration_ms: number;
  status: "ok" | "error";
  user_message?: string | null;
  agent_response?: string | null;
  spans: TraceSpan[];
  jaeger_url?: string | null;
}

export interface PolicyRule {
  tool: string;
  action_name: string;
  policy: "Allowed" | "Denied" | "Approval Required";
  description: string;
  checks: string[];
}

export interface PolicyConfig {
  agent_id: string;
  agent_name: string;
  status: string;
  fail_closed_mode: boolean;
  policies: PolicyRule[];
  security_principles: string[];
}

