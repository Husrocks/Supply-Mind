import { memo, useMemo, useState, useCallback } from 'react';
import { geoNaturalEarth1, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import type { Topology, GeometryCollection } from 'topojson-specification';
import worldData from 'world-atlas/countries-110m.json';
import type { SupplierRisk } from '../../types';
import { supplierCountryFromName, riskScoreColor } from '../../utils/risk';
import { useInView } from '../../hooks/useInView';
import { Info } from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';

interface GeographicRiskMapProps {
  suppliers: SupplierRisk[];
}

interface CountryAgg {
  code: string;
  count: number;
  avgRisk: number;
  avgGeo: number;
}

function resolveCountryCode(s: SupplierRisk): string | null {
  if (s.country_code) return s.country_code;
  return supplierCountryFromName(s.supplier_name);
}

export const GeographicRiskMap = memo(function GeographicRiskMap({ suppliers }: GeographicRiskMapProps) {
  const { ref, inView } = useInView();
  const [hover, setHover] = useState<CountryAgg | null>(null);

  const countryAgg = useMemo(() => {
    const map = new Map<string, { total: number; geo: number; count: number }>();
    for (const s of suppliers) {
      const code = resolveCountryCode(s);
      if (!code) continue;
      const cur = map.get(code) ?? { total: 0, geo: 0, count: 0 };
      cur.total += s.risk_score;
      cur.geo += s.geopolitical_factor;
      cur.count += 1;
      map.set(code, cur);
    }
    return map;
  }, [suppliers]);

  const geo = useMemo(() => {
    if (!inView) return null;
    const topology = worldData as unknown as Topology<{ countries: GeometryCollection }>;
    const countries = feature(topology, topology.objects.countries);
    const projection = geoNaturalEarth1().fitSize([720, 360], countries);
    const path = geoPath(projection);
    return { countries, path };
  }, [inView]);

  const colorFor = useCallback((isoNumeric: string) => {
    const code = ISO_NUM_TO_ALPHA3[isoNumeric];
    if (!code) return 'rgba(30,41,59,0.6)';
    const agg = countryAgg.get(code);
    if (!agg) return 'rgba(30,41,59,0.6)';
    const blend = (agg.total / agg.count) * 0.6 + (agg.geo / agg.count) * 0.4;
    return riskScoreColor(blend);
  }, [countryAgg]);

  return (
    <GlassCard accent="indigo" className="!p-0 overflow-hidden">
      <div className="p-6 pb-2">
        <h3 className="text-base font-semibold text-ink flex items-center gap-2">
          Geographic Risk Map
          <span title="Shows where your suppliers are located across the world. Red countries indicate suppliers with a high risk of delays or disruptions." className="flex items-center">
            <Info size={16} className="text-muted hover:text-indigo-400 cursor-help transition-colors" />
          </span>
        </h3>
        <p className="text-xs text-muted mt-1">Colored by API country_code + geopolitical_factor blend</p>
      </div>
      <div ref={ref} className="px-4 pb-4">
        {!inView ? (
          <div className="h-[360px] flex items-center justify-center text-muted text-sm">Loading map…</div>
        ) : geo ? (
          <div className="relative">
            <svg viewBox="0 0 720 360" className="w-full h-auto">
              {geo.countries.features.map((f) => (
                <path
                  key={f.id as string}
                  d={geo.path(f) ?? ''}
                  fill={colorFor(String(f.id))}
                  stroke="rgba(148,163,184,0.2)"
                  strokeWidth={0.5}
                  onMouseEnter={() => {
                    const code = ISO_NUM_TO_ALPHA3[String(f.id)];
                    const agg = code ? countryAgg.get(code) : undefined;
                    if (agg && code) {
                      setHover({
                        code,
                        count: agg.count,
                        avgRisk: agg.total / agg.count,
                        avgGeo: agg.geo / agg.count,
                      });
                    } else {
                      setHover(null);
                    }
                  }}
                  onMouseLeave={() => setHover(null)}
                />
              ))}
            </svg>
            {hover && (
              <div className="absolute top-2 right-2 glass-card !p-3 text-xs pointer-events-none">
                <p className="font-semibold text-ink">{hover.code}</p>
                <p className="text-body">{hover.count} supplier{hover.count !== 1 ? 's' : ''}</p>
                <p className="font-mono tabular-nums text-ink">{(hover.avgRisk * 100).toFixed(0)}% avg risk</p>
                <p className="font-mono tabular-nums text-muted">{(hover.avgGeo * 100).toFixed(0)}% geo factor</p>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </GlassCard>
  );
});

const ISO_NUM_TO_ALPHA3: Record<string, string> = {
  '156': 'CHN', '276': 'DEU', '356': 'IND', '124': 'CAN', '704': 'VNM', '566': 'NGA',
  '158': 'TWN', '410': 'KOR', '484': 'MEX', '840': 'USA', '392': 'JPN', '076': 'BRA',
};
