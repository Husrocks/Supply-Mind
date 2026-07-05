import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { AlertCircle } from 'lucide-react';
import { useDashboardQueries } from '../hooks/useDashboardQueries';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';
import { SupplierPanel } from '../components/SupplierPanel';
import { KpiCard } from '../components/ui/KpiCard';
import { AgentStatusWidget } from '../components/widgets/AgentStatusWidget';
import { AlertCenter } from '../components/widgets/AlertCenter';
import { ComparisonCards } from '../components/widgets/ComparisonCards';
import { GeographicRiskMap } from '../components/charts/GeographicRiskMap';
import { SupplierTreemap } from '../components/charts/SupplierTreemap';
import { SankeyFlow } from '../components/charts/SankeyFlow';
import { DemandForecastChart } from '../components/charts/DemandForecastChart';
import { SupplierTable } from '../components/tables/SupplierTable';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import { buildAlerts, benchmarkMetrics, buildSupplierSparklines } from '../utils/alerts';
import { riskScoreColor } from '../utils/risk';
import type { SupplierRisk } from '../types';

const getLinkColor = () => '#1e293b';

export function NetworkDashboard() {
  const { risk, inventory, pending, actions, scheduler, shouldAnimateEntry } = useDashboardQueries();
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierRisk | null>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 800, height: 420 });
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const data = risk.data;
  const isLoading = risk.isLoading;
  const error = risk.error;

  useEffect(() => {
    if (!containerRef.current) return;
    let resizeTimer: any;
    const handleResize = () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (containerRef.current) {
          setDimensions({
            width: containerRef.current.clientWidth,
            height: containerRef.current.clientHeight,
          });
        }
      }, 150);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(resizeTimer);
    };
  }, [isLoading]);

  const graphData = useMemo(() => {
    if (!data?.supplier_risks) return { nodes: [], links: [] };
    const hub = data.warehouse_nodes?.[0] ?? { id: 'WH-001', name: 'Central Distribution Hub' };
    const centralHub = { id: hub.id, name: hub.name, risk_score: 0, val: 16, isHub: true };
    const supplierNodes = data.supplier_risks.map((s) => ({
      ...s,
      id: s.supplier_id,
      name: s.supplier_name,
      val: 8,
      isHub: false,
    }));
    const links = (data.network_links ?? supplierNodes.map((s) => ({ source: s.id, target: hub.id }))).map(
      (l) => ({ source: l.source, target: l.target }),
    );
    return {
      nodes: [centralHub, ...supplierNodes],
      links,
    };
  }, [data]);

  const getNodeColor = useCallback((node: any) => {
    if (node.isHub) return '#06b6d4';
    return riskScoreColor(node.risk_score);
  }, []);

  const handleNodeClick = useCallback((node: any) => {
    if (node.isHub) return;
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 1000);
      graphRef.current.zoom(5, 1200);
    }
    setSelectedSupplier(node);
    setIsPanelOpen(true);
  }, []);

  const alerts = useMemo(
    () => buildAlerts(data?.supplier_risks ?? [], inventory.data ?? [], pending.data ?? []),
    [data, inventory.data, pending.data],
  );

  const benchmarks = useMemo(
    () => benchmarkMetrics(data?.supplier_risks ?? [], pending.data ?? [], actions.data ?? [], data?.risk_trends),
    [data, pending.data, actions.data],
  );

  const sparklines = useMemo(
    () => buildSupplierSparklines(data?.supplier_risks ?? [], data?.risk_trends),
    [data],
  );

  // Most recent action for real last-trigger-type display
  const lastAction = useMemo(() => {
    const all = actions.data ?? [];
    if (!all.length) return undefined;
    return [...all].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
  }, [actions.data]);

  if (isLoading) {
    return <ViewSkeleton />;
  }

  if (error) {
    return (
      <div className="p-8 flex items-center gap-3 glass-card max-w-lg mx-auto mt-12">
        <AlertCircle className="text-risk-high" />
        <p className="text-sm text-body">Unable to load /predictions/risk-context</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <Stagger animate={shouldAnimateEntry} className="p-5 lg:p-6 space-y-5 max-w-[1400px] mx-auto">
        <StaggerItem className="relative overflow-hidden rounded-2xl border border-white/5 min-h-[320px] flex items-center bg-[#0a0a0b]">
          <div className="absolute inset-0 z-0">
            <img src="/hero.png" alt="Supply Chain AI" className="w-full h-full object-cover opacity-50 mix-blend-screen" />
            <div className="absolute inset-0 bg-gradient-to-r from-[#0a0a0b] via-[#0a0a0b]/80 to-transparent" />
            <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0b] to-transparent opacity-80" />
          </div>
          
          <div className="relative z-10 p-8 lg:p-12 max-w-2xl">
            <h1 className="text-3xl lg:text-4xl xl:text-5xl font-bold text-white mb-3 tracking-tight leading-tight">
              Command Center
            </h1>
            <p className="text-slate-400 text-sm lg:text-base leading-relaxed mb-6 max-w-xl">
              Real-time risk prediction and autonomous supply chain intelligence.
            </p>
            <div className="flex items-center gap-4">
              <button className="btn-primary" onClick={() => document.getElementById('alert-center')?.scrollIntoView({ behavior: 'smooth' })}>
                View Active Alerts
              </button>
            </div>
          </div>
        </StaggerItem>

        <StaggerItem className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <KpiCard 
            label="Platform risk" 
            value={(data?.overall_risk_score ?? 0) * 100} 
            format={(v) => `${v.toFixed(0)}%`} 
            accent="rose" 
            tooltip="The overall health and stability score of your entire supply chain network."
          />
          <KpiCard 
            label="Anomalies" 
            value={data?.anomaly_count ?? 0} 
            accent="amber" 
            tooltip="Spikes in demand or unusual supplier behavior detected by our AI models. Click to view alerts!"
            onClick={() => {
              document.getElementById('alert-center')?.scrollIntoView({ behavior: 'smooth' });
            }}
          />
          <KpiCard 
            label="Suppliers" 
            value={data?.supplier_risks?.length ?? 0} 
            accent="indigo" 
            tooltip="The total number of suppliers actively being monitored across your network."
          />
          <div className="col-span-2 lg:col-span-2">
            <AgentStatusWidget
              health={scheduler.data}
              isLoading={scheduler.isLoading}
              isError={scheduler.isError}
              lastAction={lastAction}
            />
          </div>
        </StaggerItem>

        <StaggerItem>
          <ComparisonCards metrics={benchmarks} />
        </StaggerItem>

        <StaggerItem>
          <div id="alert-center">
            <AlertCenter 
              alerts={alerts} 
              onAlertClick={(a) => {
                if (a.supplierId && data?.supplier_risks) {
                  const s = data.supplier_risks.find(r => r.supplier_id === a.supplierId);
                  if (s) {
                    setSelectedSupplier(s);
                    setIsPanelOpen(true);
                  }
                }
              }}
            />
          </div>
        </StaggerItem>

        <StaggerItem>
          <div ref={containerRef} className="glass-card !p-0 overflow-hidden h-[420px] bg-canvas relative">
            <div className="absolute top-3 left-3 z-10 pointer-events-none bg-slate-950/85 backdrop-blur-xs border border-hairline px-3 py-1.5 rounded-xl">
              <span className="text-[10px] uppercase tracking-wider text-muted font-semibold">Supply Network Topology</span>
            </div>
            <div className="absolute bottom-3 left-3 z-10 bg-slate-950/85 backdrop-blur-xs border border-hairline px-4 py-2 rounded-xl flex items-center gap-4 text-xs pointer-events-auto">
              <span className="text-muted text-[10px] uppercase font-bold mr-1">Node Legend:</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#06b6d4]" /> Central Hub</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#10b981]" /> Low Risk</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]" /> Elevated Risk</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#f43f5e]" /> Critical Risk</span>
            </div>
            <ForceGraph2D
              ref={graphRef}
              width={dimensions.width}
              height={dimensions.height}
              graphData={graphData}
              nodeColor={getNodeColor}
              nodeRelSize={6}
              linkColor={getLinkColor}
              linkWidth={2}
              onNodeClick={handleNodeClick}
              backgroundColor="#030712"
              enableZoomInteraction={false}
            />
          </div>
        </StaggerItem>

        <StaggerItem className="grid lg:grid-cols-2 gap-4">
          <GeographicRiskMap suppliers={data?.supplier_risks ?? []} />
          <SupplierTreemap 
            suppliers={data?.supplier_risks ?? []} 
            onSelectSupplier={(s) => { setSelectedSupplier(s); setIsPanelOpen(true); }}
          />
        </StaggerItem>

        <StaggerItem className="grid lg:grid-cols-2 gap-4">
          <SankeyFlow
            suppliers={data?.supplier_risks ?? []}
            forecasts={data?.demand_forecasts ?? []}
            supplyFlows={data?.supply_flows}
          />
          <DemandForecastChart forecasts={data?.demand_forecasts ?? []} />
        </StaggerItem>

        <StaggerItem>
          <SupplierTable
            suppliers={data?.supplier_risks ?? []}
            skuSparklines={sparklines}
            onSelect={(s) => { setSelectedSupplier(s); setIsPanelOpen(true); }}
          />
        </StaggerItem>
      </Stagger>

      <SupplierPanel
        supplier={selectedSupplier}
        isOpen={isPanelOpen}
        onClose={() => {
          setIsPanelOpen(false);
          if (graphRef.current) graphRef.current.zoom(2, 800);
        }}
      />
    </div>
  );
}

export default NetworkDashboard;
