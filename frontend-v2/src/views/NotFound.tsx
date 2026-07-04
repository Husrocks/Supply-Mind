import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowRight } from 'lucide-react';
import { GlassCard } from '../components/ui/GlassCard';

export function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="flex items-center justify-center min-h-[70vh] p-6">
      <GlassCard accent="rose" className="max-w-md w-full text-center space-y-5">
        <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto">
          <ShieldAlert className="text-risk-high" size={24} />
        </div>
        <div className="space-y-2">
          <h1 className="text-lg font-semibold text-ink">404: Resource Not Found</h1>
          <p className="text-xs text-body leading-relaxed">
            The page or configuration node you requested could not be resolved in the current network topology.
          </p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="btn-primary w-full !h-9 text-xs flex items-center justify-center gap-1.5"
        >
          Return to Command Center <ArrowRight size={12} />
        </button>
      </GlassCard>
    </div>
  );
}

export default NotFound;
