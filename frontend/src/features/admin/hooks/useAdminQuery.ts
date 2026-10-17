import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../api/client';
import { queryKeys } from '../../../api/queryKeys';

export function useAdminStats() {
  return useQuery({
    queryKey: queryKeys.admin.stats(),
    queryFn: async () => {
      return api.get('/api/v1/auth/admin/stats/');
    },
  });
}

export function useAdminAuditLogs(params?: { page?: number; action?: string; search?: string }) {
  return useQuery({
    queryKey: queryKeys.admin.audit(params?.page),
    queryFn: async () => {
      const query = new URLSearchParams(params as Record<string, string>).toString();
      const qs = query ? `?${query}` : '';
      return api.get(`/api/v1/auth/admin/audit-logs/${qs}`);
    },
  });
}

export function useAdminReports(params?: Record<string, any>) {
  return useQuery({
    queryKey: queryKeys.admin.reports(),
    queryFn: async () => {
      const qs = params ? `?${new URLSearchParams(params as Record<string, string>).toString()}` : '';
      return api.get(`/api/v1/moderation/reports/${qs}`);
    },
  });
}

export function useAdminSystemHealth() {
  return useQuery({
    queryKey: queryKeys.admin.systemHealth(),
    queryFn: async () => {
      return api.get('/api/v1/health/');
    },
    refetchInterval: 60000,
  });
}

export function useResolveReportMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reportId, data }: { reportId: number; data: { action: string; note?: string } }) =>
      api.post(`/api/v1/moderation/reports/${reportId}/resolve/`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.reports() });
    },
  });
}
