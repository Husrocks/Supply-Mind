import type { RiskAccent } from '../types';

export function riskScoreColor(score: number): string {
  if (score < 0.4) return '#10b981';
  if (score <= 0.7) return '#f59e0b';
  return '#f43f5e';
}

export function riskScoreAccent(score: number): RiskAccent {
  if (score < 0.4) return 'emerald';
  if (score <= 0.7) return 'amber';
  return 'rose';
}

export function statusAccent(status: string): RiskAccent {
  if (status === 'CRITICAL' || status === 'REJECTED') return 'rose';
  if (status === 'ELEVATED' || status === 'PENDING') return 'amber';
  if (status === 'EXECUTED' || status === 'NORMAL') return 'emerald';
  return 'indigo';
}

const NAME_COUNTRY_MAP: [string, string][] = [
  ['shenzhen', 'CHN'], ['china', 'CHN'], ['hanoi', 'VNM'], ['vietnam', 'VNM'],
  ['berlin', 'DEU'], ['germany', 'DEU'], ['chennai', 'IND'], ['india', 'IND'],
  ['toronto', 'CAN'], ['canada', 'CAN'], ['lagos', 'NGA'], ['nigeria', 'NGA'],
  ['taiwan', 'TWN'], ['korea', 'KOR'], ['mexico', 'MEX'], ['usa', 'USA'],
  ['foxconn', 'TWN'], ['samsung', 'KOR'],
];

export function supplierCountryFromName(name: string): string | null {
  const lower = name.toLowerCase();
  for (const [token, code] of NAME_COUNTRY_MAP) {
    if (lower.includes(token)) return code;
  }
  return null;
}

export function skuCategory(skuId: string): string {
  const prefix = skuId.split(/[-_]/)[0];
  return prefix || skuId;
}

export function leadTimeDaysFromVariance(variance: number): number {
  return Math.round(variance * 35 + 7);
}

export function binLeadTimeDays(days: number): string {
  if (days <= 7) return '0–7 days';
  if (days <= 14) return '8–14 days';
  if (days <= 21) return '15–21 days';
  if (days <= 28) return '22–28 days';
  return '29+ days';
}

export function tierFromStatus(status: string): 'Tier 1' | 'Tier 2' | 'Tier 3' {
  const s = status.toUpperCase();
  if (s === 'PENDING') return 'Tier 2';
  if (s === 'REJECTED') return 'Tier 3';
  return 'Tier 1';
}
