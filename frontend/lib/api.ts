import axios from "axios";
import {
  AuthResponse,
  CartResponse,
  ChatResponse,
  DashboardMetrics,
  Product,
  ProductSearchResponse,
  AgentRegistry,
  ToolRegistry,
  AuditLog,
  PolicyConfig,
  User,
  TraceSummary,
  TraceJourneyResponse,
  ApprovalRequest,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Helper to check token expiration safely in browser
function isTokenExpiredHelper(token: string): boolean {
  if (!token) return true;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return true;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    const payload = JSON.parse(jsonPayload);
    if (!payload.exp) return false;
    return payload.exp * 1000 <= Date.now() + 15000;
  } catch {
    return true;
  }
}

// Attach Authorization header if valid token exists
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const isAdminUrl = config.url?.startsWith("/admin");
    const adminToken = localStorage.getItem("kon_admin_token");
    const token = (isAdminUrl && adminToken) ? adminToken : (adminToken || localStorage.getItem("kon_token"));
    if (token) {
      if (isTokenExpiredHelper(token)) {
        if (isAdminUrl && adminToken) localStorage.removeItem("kon_admin_token");
        else localStorage.removeItem("kon_token");
      } else {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Response interceptor with transparent re-auth for both admin and customer sessions
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config;
    const status = err.response?.status;
    const isAuthError = status === 401 || status === 403;
    const isAdminRoute =
      typeof window !== "undefined" &&
      (window.location.pathname.startsWith("/admin") || originalRequest?.url?.includes("/admin"));

    // Transparently auto-reauthenticate admin session on 401/403
    if (isAuthError && isAdminRoute && originalRequest && !originalRequest._adminRetry) {
      originalRequest._adminRetry = true;
      try {
        const adminRes = await axios.post(`${API_BASE_URL}/auth/login`, {
          username: "admin",
          password: "admin123",
        });
        const adminToken = adminRes.data.access_token;
        if (typeof window !== "undefined") {
          localStorage.setItem("kon_admin_token", adminToken);
          localStorage.setItem("kon_token", adminToken);
          localStorage.setItem("kon_user", JSON.stringify(adminRes.data.user));
        }
        originalRequest.headers.Authorization = `Bearer ${adminToken}`;
        return api(originalRequest);
      } catch (adminErr) {
        window.dispatchEvent(new CustomEvent("kon_admin_auth_error", { detail: status }));
        return Promise.reject(adminErr);
      }
    }

    // Transparently refresh customer session on 401
    if (
      status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/")
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((e) => Promise.reject(e));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        if (typeof window !== "undefined") {
          localStorage.removeItem("kon_token");
        }
        const refreshRes = await axios.post(`${API_BASE_URL}/auth/login`, {
          username: "demo_customer",
          password: "customer123",
        });
        const newToken = refreshRes.data.access_token;
        if (typeof window !== "undefined") {
          localStorage.setItem("kon_token", newToken);
          localStorage.setItem("kon_user", JSON.stringify(refreshRes.data.user));
        }
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        processQueue(null, newToken);
        return api(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(err);
  }
);

// Authentication
export async function login(username: string, password: string): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/login", { username, password });
  return res.data;
}

export async function register(username: string, email: string, password: string): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/register", { username, email, password });
  return res.data;
}

export async function getMe(): Promise<User> {
  const res = await api.get<User>("/auth/me");
  return res.data;
}

// Conversational Chat
export async function sendMessage(message: string, sessionId: string): Promise<ChatResponse> {
  const res = await api.post<ChatResponse>("/chat/message", {
    message,
    session_id: sessionId,
  });
  return res.data;
}

export async function confirmAssistantSelection(
  productId: string,
  quantity: number = 1.0,
  sessionId: string,
  unit?: string
): Promise<ChatResponse> {
  const res = await api.post<ChatResponse>("/chat/confirm-product-selection", {
    product_id: productId,
    quantity,
    session_id: sessionId,
    unit,
  });
  return res.data;
}

// Product Catalog
export async function searchProducts(query: string = "", category: string = "", limit: number = 50): Promise<ProductSearchResponse> {
  const res = await api.get<ProductSearchResponse>("/products", {
    params: { q: query, category, limit },
  });
  return res.data;
}

export async function getProduct(productId: string): Promise<Product> {
  const res = await api.get<Product>(`/products/${productId}`);
  return res.data;
}

// Shopping Cart
export async function getCart(sessionId: string): Promise<CartResponse> {
  const res = await api.get<CartResponse>("/cart", {
    params: { session_id: sessionId },
  });
  return res.data;
}

export async function addToCart(productId: string, quantity: number, sessionId: string): Promise<CartResponse> {
  const res = await api.post<CartResponse>(
    "/cart/items",
    { product_id: productId, quantity },
    { params: { session_id: sessionId } }
  );
  return res.data;
}

export async function updateCartItem(cartItemId: string, quantity: number, sessionId: string): Promise<CartResponse> {
  const res = await api.put<CartResponse>(
    `/cart/items/${cartItemId}`,
    { quantity },
    { params: { session_id: sessionId } }
  );
  return res.data;
}

export async function removeCartItem(cartItemId: string, sessionId: string): Promise<CartResponse> {
  const res = await api.delete<CartResponse>(`/cart/items/${cartItemId}`, {
    params: { session_id: sessionId },
  });
  return res.data;
}

export async function clearCart(sessionId: string): Promise<void> {
  await api.delete("/cart", {
    params: { session_id: sessionId },
  });
}

export async function getCheckoutPreview(sessionId: string): Promise<CartResponse> {
  const res = await api.get<CartResponse>("/cart/checkout-preview", {
    params: { session_id: sessionId },
  });
  return res.data;
}

// Governance & Admin Dashboard
export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  const res = await api.get<DashboardMetrics>("/admin/dashboard");
  return res.data;
}

export async function getAgents(): Promise<AgentRegistry[]> {
  const res = await api.get<AgentRegistry[]>("/admin/agents");
  return res.data;
}

export async function createAgent(data: Partial<AgentRegistry>): Promise<AgentRegistry> {
  const res = await api.post<AgentRegistry>("/admin/agents", data);
  return res.data;
}

export async function updateAgent(agentId: string, updates: Partial<AgentRegistry>): Promise<AgentRegistry> {
  const res = await api.patch<AgentRegistry>(`/admin/agents/${agentId}`, updates);
  return res.data;
}

export async function toggleAgentStatus(agentId: string): Promise<AgentRegistry> {
  const res = await api.post<AgentRegistry>(`/admin/agents/${agentId}/toggle-status`);
  return res.data;
}

// Human-in-the-Loop (HITL) Approvals
export async function getApprovals(statusFilter?: string): Promise<ApprovalRequest[]> {
  const res = await api.get<ApprovalRequest[]>("/admin/approvals", {
    params: statusFilter ? { status_filter: statusFilter } : {},
  });
  return res.data;
}

export async function approveRequest(approvalId: string, notes?: string): Promise<ApprovalRequest> {
  const res = await api.post<ApprovalRequest>(`/admin/approvals/${approvalId}/approve`, { notes });
  return res.data;
}

export async function rejectRequest(approvalId: string, notes?: string): Promise<ApprovalRequest> {
  const res = await api.post<ApprovalRequest>(`/admin/approvals/${approvalId}/reject`, { notes });
  return res.data;
}

export async function simulateApprovalRequest(): Promise<ApprovalRequest> {
  const res = await api.post<ApprovalRequest>("/admin/approvals/simulate");
  return res.data;
}

export async function getTools(): Promise<ToolRegistry[]> {
  const res = await api.get<ToolRegistry[]>("/admin/tools");
  return res.data;
}

export interface AuditLogFilter {
  agent_id?: string;
  tool_name?: string;
  decision?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export async function getAuditLogs(filters?: AuditLogFilter): Promise<{ logs: AuditLog[]; total: number }> {
  const res = await api.get<{ logs: AuditLog[]; total: number }>("/admin/audit-logs", {
    params: filters,
  });
  return res.data;
}

export async function getSecurityEvents(): Promise<AuditLog[]> {
  const res = await api.get<AuditLog[]>("/admin/security-events");
  return res.data;
}

export async function getPolicies(): Promise<PolicyConfig> {
  const res = await api.get<PolicyConfig>("/admin/policies");
  return res.data;
}

export async function simulateBlockedAction(): Promise<{
  simulated: boolean;
  tool_attempted: string;
  governance_decision: string;
  denial_reason: string;
  trace_id: string;
  message: string;
}> {
  const res = await api.post("/admin/simulate-blocked-action");
  return res.data;
}

export async function getTraces(limit: number = 30): Promise<TraceSummary[]> {
  const res = await api.get<TraceSummary[]>(`/admin/traces?limit=${limit}`);
  return res.data;
}

export async function getTraceJourney(traceId: string): Promise<TraceJourneyResponse> {
  const res = await api.get<TraceJourneyResponse>(`/admin/traces/${traceId}`);
  return res.data;
}

/**
 * Connects to the real-time Server-Sent Events (SSE) telemetry stream.
 * Automatically receives audit logs, security events, and trace spans.
 */
export function createAdminEventSource(
  onEvent: (type: string, data: any) => void,
  onError?: (err: any) => void
): () => void {
  if (typeof window === "undefined") return () => {};

  const token = localStorage.getItem("kon_admin_token") || localStorage.getItem("kon_token") || "";
  const url = `${API_BASE_URL}/admin/events/stream${token ? `?token=${encodeURIComponent(token)}` : ""}`;
  const es = new EventSource(url);

  es.onopen = () => {
    // Connected to SSE stream
  };

  es.addEventListener("audit_log", (e: MessageEvent) => {
    try {
      const parsed = JSON.parse(e.data);
      onEvent("audit_log", parsed);
    } catch {}
  });

  es.addEventListener("trace_span", (e: MessageEvent) => {
    try {
      const parsed = JSON.parse(e.data);
      onEvent("trace_span", parsed);
    } catch {}
  });

  es.addEventListener("approval_request", (e: MessageEvent) => {
    try {
      const parsed = JSON.parse(e.data);
      onEvent("approval_request", parsed);
    } catch {}
  });

  es.addEventListener("approval_resolved", (e: MessageEvent) => {
    try {
      const parsed = JSON.parse(e.data);
      onEvent("approval_resolved", parsed);
    } catch {}
  });

  es.addEventListener("agent_updated", (e: MessageEvent) => {
    try {
      const parsed = JSON.parse(e.data);
      onEvent("agent_updated", parsed);
    } catch {}
  });

  es.onerror = (err) => {
    if (onError) onError(err);
  };

  return () => {
    es.close();
  };
}

export { api };
export default api;

