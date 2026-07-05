import axios from 'axios';

const apiURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const apiClient = axios.create({
  baseURL: `${apiURL}/api/v1`,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

export const healthClient = axios.create({
  baseURL: apiURL,
  timeout: 5000,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('supplymind_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('supplymind_token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const getPendingActions = async (params?: { supplier_id?: string; sku_id?: string }) => {
  const response = await apiClient.get('/agent/actions', { params: { status: 'PENDING', ...params } });
  return response.data;
};

export const getAllActions = async (params?: { supplier_id?: string; sku_id?: string }) => {
  const response = await apiClient.get('/agent/actions', { params });
  return response.data;
};

export const approveAction = async (actionId: string, username = 'AdminUser') => {
  const response = await apiClient.post(`/agent/actions/${actionId}/approve`, {
    approved_by: username,
    notes: 'Approved via Override Console',
  });
  return response.data;
};

export const rejectAction = async (actionId: string, reason: string, username = 'AdminUser') => {
  const response = await apiClient.post(`/agent/actions/${actionId}/reject`, {
    rejected_by: username,
    reason,
  });
  return response.data;
};

export const deleteAction = async (actionId: string) => {
  const response = await apiClient.delete(`/agent/actions/${actionId}`);
  return response.data;
};

export const getAuditLog = async (page = 1, pageSize = 100) => {
  const response = await apiClient.get('/audit/reasoning-log', {
    params: { page, page_size: pageSize },
  });
  const data = response.data;
  const entries = data.entries ?? data.logs ?? [];
  return {
    logs: entries.map((e: Record<string, unknown>) => ({
      action_id: Number(e.log_id ?? e.action_id ?? 0),
      action_plan_id: String(e.correlation_id ?? e.action_plan_id ?? '').replace('corr-', ''),
      action_type: String(e.event_type ?? e.action_type ?? 'action_generated'),
      status: String((e.metadata as Record<string, unknown>)?.status ?? e.status ?? 'EXECUTED'),
      sku_id: String(e.sku_id ?? '—'),
      supplier_id: String(e.supplier_id ?? '—'),
      estimated_cost_usd: Number((e.metadata as Record<string, unknown>)?.cost_usd ?? e.estimated_cost_usd ?? 0),
      reasoning: String(e.reasoning_trace ?? e.reasoning ?? ''),
      timestamp: String(e.timestamp ?? ''),
    })),
    total: data.total ?? entries.length,
    page: data.page ?? page,
    has_next: data.has_next ?? false,
  };
};

export const getInventoryRisk = async () => {
  const response = await apiClient.get('/inventory/risk-heatmap');
  return response.data;
};

export const getModelPerformance = async () => {
  const response = await apiClient.get('/models/performance');
  return response.data;
};

export const getRiskContext = async () => {
  const response = await apiClient.get('/predictions/risk-context');
  return response.data;
};

export const getSchedulerStatus = async () => {
  const response = await apiClient.get('/scheduler/status');
  return response.data;
};

export const getSchedulerHealth = async () => {
  const response = await healthClient.get('/health');
  return response.data;
};

// ── Supplier Onboarding ────────────────────────────────────────────────────────

export const getOnboardingList = async (status?: string) => {
  const params = status ? { status } : {};
  const response = await apiClient.get('/suppliers/onboarding', { params });
  return response.data;
};

export const postOnboardSupplier = async (data: {
  supplier_id: string;
  supplier_name: string;
  credentials_data?: Record<string, unknown>;
  geographic_risk_region?: string;
  capacity_info?: Record<string, unknown>;
  reference_check_status?: string;
}) => {
  const response = await apiClient.post('/suppliers/onboard', data);
  return response.data;
};

export const postStartProbation = async (onboardingId: number) => {
  const response = await apiClient.post(`/suppliers/onboarding/${onboardingId}/start-probation`);
  return response.data;
};

export const patchProbationMetrics = async (
  onboardingId: number,
  metrics: { probation_on_time_rate: number; probation_rejection_rate: number; probation_po_count: number }
) => {
  const response = await apiClient.patch(`/suppliers/onboarding/${onboardingId}/metrics`, metrics);
  return response.data;
};

export const postEvaluateOnboarding = async (onboardingId: number) => {
  const response = await apiClient.post(`/suppliers/onboarding/${onboardingId}/evaluate`);
  return response.data;
};

// ── Settings ──────────────────────────────────────────────────────────────────
export const getSettings = async () => {
  const response = await apiClient.get('/settings');
  return response.data;
};

export const updateSettings = async (data: {
  risk_high_threshold: number;
  risk_critical_threshold: number;
  stockout_warning_days: number;
  autonomous_budget_usd: number;
  anomaly_reconstruction_percentile: number;
  manager_email: string;
}) => {
  const response = await apiClient.put('/settings', data);
  return response.data;
};

// ── Single Supplier & SKU Details ──────────────────────────────────────────────
export const getSupplierDetail = async (supplierId: string) => {
  const response = await apiClient.get(`/suppliers/${supplierId}`);
  return response.data;
};

export const getSkuDetail = async (skuId: string) => {
  const response = await apiClient.get(`/inventory/${skuId}`);
  return response.data;
};

export const triggerAgentAnalysis = async (supplierId: string, skuId = 'FOODS_1_001_CA_1_evaluation') => {
  const response = await apiClient.post('/agent/trigger', {
    primary_supplier_id: supplierId,
    trigger_type: 'MANUAL',
    sku_id: skuId,
  });
  return response.data;
};

export const getRetrainStatus = async (modelName?: string) => {
  const params = modelName ? { model_name: modelName } : {};
  const response = await apiClient.get('/models/retrain/status', { params });
  return response.data;
};

export const getRetrainLogsUrl = (jobId: number) => {
  return `${apiClient.defaults.baseURL}/models/retrain/${jobId}/logs`;
};

export const getSkuRiskContext = async (skuId: string, supplierId: string, currentInventory = 5000, alternativeSuppliers: string[] = []) => {
  const params = new URLSearchParams();
  params.append('supplier_id', supplierId);
  params.append('current_inventory', currentInventory.toString());
  alternativeSuppliers.forEach(alt => params.append('alternative_supplier_ids', alt));
  
  const response = await apiClient.get(`/predictions/risk-context/${skuId}?${params.toString()}`);
  return response.data;
};
