import { useState, useEffect, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { SupplierDetailPanel } from '../components/SupplierDetailPanel';
import type { SupplierContext, SupplierNode, SupplierLink } from '../types';
import { ShieldAlert, Network, Loader2 } from 'lucide-react';
import { usePolling } from '../hooks/usePolling';
import { ErrorBoundary } from '../components/ErrorBoundary';

export function Dashboard() {
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierContext | null>(null);
  const [graphData, setGraphData] = useState<{ nodes: SupplierNode[], links: SupplierLink[] }>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [dimensions, setDimensions] = useState({ width: window.innerWidth, height: window.innerHeight - 64 });
  const graphRef = useRef<any>(null);

  // Resize handler
  useEffect(() => {
    const handleResize = () => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight - 64
      });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const fetchNetworkData = useCallback(() => {
    // In Phase 4, this simulates an API call or re-fetches real data
    const mockNodes: SupplierNode[] = [
      { id: 'SUP-0001', name: 'Shenzhen Components Ltd', risk_score: 0.85, val: 1.5 },
      { id: 'SUP-0002', name: 'Foxconn Primary', risk_score: 0.2, val: 1 },
      { id: 'SUP-0003', name: 'Taiwan Semicond', risk_score: 0.15, val: 1 },
      { id: 'SUP-0004', name: 'Samsung Electronics', risk_score: 0.55, val: 1 },
      { id: 'SUP-0005', name: 'Global Foundries', risk_score: 0.35, val: 1 },
    ];
    
    const mockLinks: SupplierLink[] = [
      { source: 'SUP-0001', target: 'SUP-0002' },
      { source: 'SUP-0001', target: 'SUP-0003' },
      { source: 'SUP-0002', target: 'SUP-0004' },
      { source: 'SUP-0004', target: 'SUP-0005' },
      { source: 'SUP-0003', target: 'SUP-0005' },
    ];

    setGraphData({ nodes: mockNodes, links: mockLinks });
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchNetworkData();
  }, [fetchNetworkData]);

  // Phase 4: Real-time polling
  usePolling(fetchNetworkData, 30000);

  const getNodeColor = (node: any) => {
    if (node.risk_score < 0.4) return '#34d399'; // emerald-400
    if (node.risk_score <= 0.7) return '#fbbf24'; // amber-400
    return '#f43f5e'; // rose-500
  };

  const handleNodeClick = useCallback((node: any) => {
    // Center graph on node
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 1000);
      graphRef.current.zoom(8, 2000);
    }
    
    // Construct mock context for panel based on selected node
    const mockContext: SupplierContext = {
      supplier_id: node.id,
      risk_score: node.risk_score,
      risk_level: node.risk_score > 0.7 ? 'CRITICAL' : node.risk_score > 0.4 ? 'ELEVATED' : 'NORMAL',
      is_anomaly: node.risk_score > 0.8,
      reconstruction_error: 0.05,
      shap_drivers: [
        { feature: 'lead_time_volatility', impact: 0.34, direction: 'increases_risk', value: 4.5 },
        { feature: 'defect_rate_spike', impact: 0.22, direction: 'increases_risk', value: 0.05 },
        { feature: 'financial_health', impact: -0.15, direction: 'decreases_risk', value: 0.9 },
      ],
      avg_lead_time_days: Math.round(node.risk_score * 40 + 10),
      on_time_delivery_pct: 1 - node.risk_score,
      po_acceptance_rate: 0.95,
      lead_time_slope_6w: 1.2,
      unit_cost_estimate: 150
    };
    
    setSelectedSupplier(mockContext);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-slate-950 overflow-hidden relative">
      <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md flex items-center px-6 z-10">
        <div className="flex items-center gap-3">
          <ShieldAlert className="text-indigo-500" size={28} />
          <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent tracking-wide">
            SupplyMind: Risk Command Center
          </h1>
        </div>
        <div className="ml-auto flex items-center gap-2 text-sm text-slate-400 bg-slate-800/50 px-3 py-1.5 rounded-full border border-slate-700/50">
          <Network size={16} className="text-slate-500" />
          <span>{loading ? "Connecting..." : `${graphData.nodes.length} Active Nodes`}</span>
        </div>
      </header>

      <main className="flex-1 relative w-full h-full">
        <ErrorBoundary>
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-[#020617]">
              <div className="flex flex-col items-center">
                <div className="animate-pulse w-32 h-32 rounded-full bg-slate-800 mb-8 border-4 border-slate-700/50" />
                <div className="flex items-center gap-3 text-indigo-400">
                  <Loader2 className="animate-spin" size={24} />
                  <span className="font-semibold tracking-wider uppercase text-sm">Building Network Topology...</span>
                </div>
              </div>
            </div>
          ) : graphData.nodes.length > 0 && (
            <ForceGraph2D
              ref={graphRef}
              width={dimensions.width}
              height={dimensions.height}
              graphData={graphData}
              nodeColor={getNodeColor}
              nodeRelSize={6}
              linkColor={() => '#334155'}
              linkWidth={1.5}
              onNodeClick={handleNodeClick}
              backgroundColor="#020617"
              nodeCanvasObjectMode={() => 'after'}
              nodeCanvasObject={(node: any, ctx, globalScale) => {
                const label = node.name || node.id;
                const fontSize = 12/globalScale;
                ctx.font = `${fontSize}px Sans-Serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
                ctx.fillText(label, node.x, node.y + 12);
              }}
            />
          )}
        </ErrorBoundary>
      </main>

      {selectedSupplier && (
        <SupplierDetailPanel 
          supplier={selectedSupplier} 
          onClose={() => setSelectedSupplier(null)} 
        />
      )}
    </div>
  );
}
