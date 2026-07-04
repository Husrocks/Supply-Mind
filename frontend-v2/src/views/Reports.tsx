import { useState } from 'react';
import { apiClient } from '../api/client';
import { 
  Download, Loader2, ShieldAlert, BarChart3, ListCollapse, FileSpreadsheet 
} from 'lucide-react';
import toast from 'react-hot-toast';
import { GlassCard } from '../components/ui/GlassCard';
import { Stagger, StaggerItem } from '../components/motion/Stagger';

export function Reports() {
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleDownload = async (type: string, title: string) => {
    setDownloading(type);
    try {
      const response = await apiClient.get('/reports/download', {
        params: { type },
        responseType: 'blob',
      });
      
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `supplymind_${type}_report_${new Date().toISOString().slice(0,10)}.csv`);
      document.body.appendChild(link);
      
      link.click();
      
      // Clean up
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success(`${title} downloaded successfully`);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Report download failed';
      toast.error(`Download failed: ${detail}`);
    } finally {
      setDownloading(null);
    }
  };

  const reportCards = [
    {
      id: 'risk',
      title: 'Weekly Risk Summary',
      description: 'Contains geopolitical factors, lead time variances, defect rates, and overall ML model disruption scores per supplier.',
      icon: ShieldAlert,
      accent: 'rose' as const,
    },
    {
      id: 'scorecard',
      title: 'Supplier Scorecard',
      description: 'Historical performance KPIs including average lead times, delivery rates, PO acceptance percentages, and unit costs.',
      icon: BarChart3,
      accent: 'cyan' as const,
    },
    {
      id: 'actions',
      title: 'Mitigation Actions Audit Log',
      description: 'Full chronological audit log of autonomous and human-mediated actions taken, including costs, status, and reasoning.',
      icon: ListCollapse,
      accent: 'indigo' as const,
    },
  ];

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6">
      <Stagger className="max-w-4xl mx-auto space-y-6">
        <StaggerItem>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-accent-indigo flex items-center justify-center">
              <FileSpreadsheet size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-ink">Analytical Reports</h1>
              <p className="text-sm text-body mt-1">Export key supply chain datasets and audit histories as CSV files.</p>
            </div>
          </div>
        </StaggerItem>

        <StaggerItem className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {reportCards.map((r) => {
            const Icon = r.icon;
            const isThisDownloading = downloading === r.id;
            return (
              <GlassCard key={r.id} accent={r.accent} className="flex flex-col h-full justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted uppercase tracking-wider">CSV Export</span>
                    <Icon size={18} className={`text-accent-${r.accent === 'rose' ? 'rose' : r.accent}`} />
                  </div>
                  <h3 className="text-base font-semibold text-ink">{r.title}</h3>
                  <p className="text-xs text-body leading-relaxed">{r.description}</p>
                </div>
                <div className="pt-5 border-t border-hairline mt-6">
                  <button
                    onClick={() => handleDownload(r.id, r.title)}
                    disabled={downloading !== null}
                    className="btn-primary w-full !h-9 text-xs flex items-center justify-center gap-1.5"
                  >
                    {isThisDownloading ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Download size={14} />
                    )}
                    {isThisDownloading ? 'Generating...' : 'Export CSV'}
                  </button>
                </div>
              </GlassCard>
            );
          })}
        </StaggerItem>
      </Stagger>
    </div>
  );
}

export default Reports;
