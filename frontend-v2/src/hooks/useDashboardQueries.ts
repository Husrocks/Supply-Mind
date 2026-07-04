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
} from '../api/client';

const POLL_MS = 60_000;

export function useRiskContext() {
  return useQuery({
    queryKey: queryKeys.riskContext,
    queryFn: fetchRiskContext,
    refetchInterval: POLL_MS,
    staleTime: POLL_MS / 2,
  });
}

export function useInventory() {
  return useQuery({
    queryKey: queryKeys.inventory,
    queryFn: fetchInventory,
    staleTime: 60_000,
  });
}

export function usePendingActions() {
  return useQuery({
    queryKey: queryKeys.pendingActions,
    queryFn: fetchPendingActions,
    refetchInterval: 60_000,
  });
}

export function useAllActions() {
  return useQuery({
    queryKey: queryKeys.allActions,
    queryFn: fetchAllActions,
    refetchInterval: POLL_MS,
  });
}

export function useAuditLog() {
  return useQuery({
    queryKey: queryKeys.auditLog,
    queryFn: fetchAuditLog,
    staleTime: 30_000,
  });
}

export function useModelPerformance() {
  return useQuery({
    queryKey: queryKeys.modelPerformance,
    queryFn: fetchModelPerformance,
    staleTime: 120_000,
  });
}

export function useSchedulerHealth() {
  return useQuery({
    queryKey: queryKeys.schedulerHealth,
    queryFn: fetchSchedulerHealth,
    refetchInterval: POLL_MS,
    retry: 1,
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

  return {
    risk: useRiskContext(),
    inventory: useInventory(),
    pending: usePendingActions(),
    actions: useAllActions(),
    audit: useAuditLog(),
    models: useModelPerformance(),
    scheduler: useSchedulerHealth(),
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
