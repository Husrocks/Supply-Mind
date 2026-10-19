import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../api/queries';
import {
  fetchRiskContext,
  fetchInventory,
  fetchPendingActions,
  fetchAllActions,
  fetchAuditLog,
  fetchModelPerformance,
  fetchSchedulerHealth,
  fetchOnboarding,
} from '../api/fetchers';
import {
  getSettings,
  getSupplierDetail,
  getSkuDetail,
  approveAction,
  rejectAction,
  postOnboardSupplier,
  postStartProbation,
  patchProbationMetrics,
  postEvaluateOnboarding,
  updateSettings,
  deleteAction,
  getRetrainStatus,
  getSkuRiskContext,
  simulateWhatIf,
  simulateSupplierDisruption,
  resetDemoState,
  getReorderRecommendations,
  updateReorderStatus,
  getSupplierExplainability,
  getSkuExplainability,
  askAssistant,
  getAssistantSuggestions,
} from '../api/client';

const POLL_MS = 240_000; // 4-minute polling interval in dev to prevent CPU / thread starvation

export function useRiskContext() {
  return useQuery({
    queryKey: queryKeys.riskContext,
    queryFn: fetchRiskContext,
    refetchInterval: POLL_MS,
    staleTime: POLL_MS / 2,
  });
}

export function useInventory(enabled = true) {
  return useQuery({
    queryKey: queryKeys.inventory,
    queryFn: fetchInventory,
    staleTime: 120_000,
    enabled,
  });
}

export function usePendingActions(enabled = true) {
  return useQuery({
    queryKey: queryKeys.pendingActions,
    queryFn: fetchPendingActions,
    refetchInterval: POLL_MS,
    staleTime: POLL_MS / 2,
    enabled,
  });
}

export function useAllActions(enabled = true) {
  return useQuery({
    queryKey: queryKeys.allActions,
    queryFn: fetchAllActions,
    refetchInterval: POLL_MS,
    staleTime: POLL_MS / 2,
    enabled,
  });
}

export function useAuditLog(enabled = true) {
  return useQuery({
    queryKey: queryKeys.auditLog,
    queryFn: fetchAuditLog,
    staleTime: 60_000,
    enabled,
  });
}

export function useModelPerformance(enabled = true) {
  return useQuery({
    queryKey: queryKeys.modelPerformance,
    queryFn: fetchModelPerformance,
    staleTime: 180_000,
    enabled,
  });
}

export function useSchedulerHealth(enabled = true) {
  return useQuery({
    queryKey: queryKeys.schedulerHealth,
    queryFn: fetchSchedulerHealth,
    refetchInterval: POLL_MS,
    retry: 1,
    enabled,
  });
}

export function useOnboarding(status?: string) {
  return useQuery({
    queryKey: [...queryKeys.onboarding, status ?? 'all'],
    queryFn: () => fetchOnboarding(status),
    refetchInterval: POLL_MS,
    staleTime: POLL_MS / 2,
  });
}

export function useDashboardQueries() {
  const queryClient = useQueryClient();
  const isCached = (key: readonly string[]) => queryClient.getQueryData(key) !== undefined;

  const risk = useRiskContext();
  const riskReady = !risk.isLoading;

  return {
    risk,
    inventory: useInventory(riskReady),
    pending: usePendingActions(riskReady),
    actions: useAllActions(riskReady),
    audit: useAuditLog(riskReady),
    models: useModelPerformance(riskReady),
    scheduler: useSchedulerHealth(riskReady),
    shouldAnimateEntry: !isCached(queryKeys.riskContext),
  };
}

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: getSettings,
    staleTime: 60_000,
  });
}

export function useSupplierDetail(supplierId: string) {
  return useQuery({
    queryKey: queryKeys.supplierDetail(supplierId),
    queryFn: () => getSupplierDetail(supplierId),
    enabled: !!supplierId,
    staleTime: 15_000,
  });
}

export function useSkuDetail(skuId: string) {
  return useQuery({
    queryKey: queryKeys.skuDetail(skuId),
    queryFn: () => getSkuDetail(skuId),
    enabled: !!skuId,
    staleTime: 15_000,
  });
}

export function useApproveAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ actionId, username }: { actionId: string; username?: string }) =>
      approveAction(actionId, username),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.pendingActions });
      queryClient.invalidateQueries({ queryKey: queryKeys.allActions });
    },
  });
}

export function useRejectAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ actionId, reason, username }: { actionId: string; reason: string; username?: string }) =>
      rejectAction(actionId, reason, username),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.pendingActions });
      queryClient.invalidateQueries({ queryKey: queryKeys.allActions });
    },
  });
}

export function useDeleteAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (actionId: string) => deleteAction(actionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.allActions });
      queryClient.invalidateQueries({ queryKey: queryKeys.auditLog });
    },
  });
}

export function useOnboardSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: postOnboardSupplier,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.onboarding });
    },
  });
}

export function useStartProbationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: postStartProbation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.onboarding });
    },
  });
}

export function useUpdateProbationMetrics() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ onboardingId, metrics }: { onboardingId: number; metrics: any }) =>
      patchProbationMetrics(onboardingId, metrics),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.onboarding });
    },
  });
}

export function useEvaluateOnboardingMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: postEvaluateOnboarding,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.onboarding });
    },
  });
}

export function useUpdateSettingsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings });
    },
  });
}

export function useRetrainStatus(modelName?: string) {
  return useQuery({
    queryKey: ['retrainStatus', modelName],
    queryFn: () => getRetrainStatus(modelName),
    refetchInterval: 10_000,
  });
}

export function useSkuRiskContextMutation() {
  return useMutation({
    mutationFn: ({ skuId, supplierId, currentInventory, alternativeSuppliers }: { skuId: string, supplierId: string, currentInventory?: number, alternativeSuppliers?: string[] }) => 
      getSkuRiskContext(skuId, supplierId, currentInventory, alternativeSuppliers)
  });
}

// ── Interactive Features React Query Hooks ──────────────────────────────────

export function useWhatIfMutation() {
  return useMutation({
    mutationFn: (params: Parameters<typeof simulateWhatIf>[0]) => simulateWhatIf(params),
  });
}

export function useSupplierDisruptionMutation() {
  return useMutation({
    mutationFn: (params: Parameters<typeof simulateSupplierDisruption>[0]) => simulateSupplierDisruption(params),
  });
}

export function useResetDemoMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resetDemoState,
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });
}

export function useReorderRecommendations(params?: {
  status?: string;
  criticality?: string;
  supplier_id?: string;
  search?: string;
}) {
  return useQuery({
    queryKey: queryKeys.reorders(params),
    queryFn: () => getReorderRecommendations(params),
    staleTime: 60_000,
  });
}

export function useUpdateReorderStatusMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ skuId, status, notes }: { skuId: string; status: 'PENDING' | 'REVIEWED' | 'DISMISSED'; notes?: string }) =>
      updateReorderStatus(skuId, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reorders'] });
    },
  });
}

export function useSupplierExplainability(supplierId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.supplierExplainability(supplierId),
    queryFn: () => getSupplierExplainability(supplierId),
    enabled: Boolean(supplierId) && enabled,
    staleTime: 300_000,
  });
}

export function useSkuExplainability(skuId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.skuExplainability(skuId),
    queryFn: () => getSkuExplainability(skuId),
    enabled: Boolean(skuId) && enabled,
    staleTime: 300_000,
  });
}

export function useAssistantChatMutation() {
  return useMutation({
    mutationFn: ({ question, history }: { question: string; history?: Array<{ role: 'user' | 'assistant'; content: string }> }) =>
      askAssistant(question, history),
  });
}

export function useAssistantSuggestions() {
  return useQuery({
    queryKey: queryKeys.assistantSuggestions,
    queryFn: getAssistantSuggestions,
    staleTime: 600_000,
  });
}
