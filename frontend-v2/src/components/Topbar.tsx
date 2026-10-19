import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { LogOut, User, Activity, Menu, Sun, Moon, RotateCcw } from 'lucide-react';
import toast from 'react-hot-toast';
import { useResetDemoMutation } from '../hooks/useDashboardQueries';

interface TopbarProps {
  onToggleSidebar?: () => void;
}

export function Topbar({ onToggleSidebar }: TopbarProps) {
  const { logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const title: Record<string, string> = {
    '/': 'Command Center',
    '/dashboard': 'Command Center',
    '/simulator': 'What-If Supply Chain Simulator',
    '/reorder': 'Smart Reorder Recommendations',
    '/disruption': 'Supplier Disruption & Recovery Simulator',
    '/assistant': 'Ask SupplyMind AI Assistant',
    '/override': 'Override Console',
    '/onboarding': 'Supplier Onboarding',
    '/audit': 'Audit Log',
    '/inventory': 'Inventory Heatmap',
    '/models': 'Model Observatory',
    '/settings': 'System Settings',
    '/reports': 'Analytical Reports',
  };

  const getPageTitle = () => {
    const path = location.pathname;
    if (title[path]) return title[path];
    if (path.startsWith('/supplier/')) return 'Supplier Profile';
    if (path.startsWith('/sku/')) return 'SKU Demand Outlook';
    return 'Dashboard';
  };

  const resetMutation = useResetDemoMutation();

  const handleReset = async () => {
    try {
      await resetMutation.mutateAsync();
      toast.success('Demo state reset to clean baseline!');
    } catch {
      toast.error('Failed to reset demo state.');
    }
  };

  return (
    <header className="h-16 border-b border-hairline bg-surface flex items-center justify-between px-4 sm:px-6 shrink-0 z-30 select-none">
      <div className="flex items-center gap-3">
        {/* Hamburger Menu Toggle: 44x44px WCAG 2.5.5 target */}
        <button
          onClick={onToggleSidebar}
          className="lg:hidden w-11 h-11 flex items-center justify-center rounded-xl bg-surface-elevated border border-hairline text-body hover:text-ink hover:bg-surface transition-colors focus-visible:outline-none touch-action-manipulation"
          title="Toggle Navigation Menu"
          aria-label="Toggle Navigation Menu"
        >
          <Menu size={20} />
        </button>

        <h2 className="text-base font-semibold text-ink tracking-tight">{getPageTitle()}</h2>
        <span className="hidden sm:flex items-center gap-1.5 text-[11px] font-medium text-muted bg-surface-elevated px-2.5 py-1 rounded-full border border-hairline">
          <Activity size={12} className="text-primary" /> Live Feeds
        </span>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Demo Mode Badge & Ergonomic Reset Button */}
        <div className="hidden md:flex items-center gap-2 bg-surface-elevated border border-hairline px-3 py-1.5 rounded-full text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-muted text-[11px] font-medium">Demo Mode</span>
          <button
            type="button"
            onClick={handleReset}
            disabled={resetMutation.isPending}
            className="text-[11px] min-h-[32px] px-2 text-accent-indigo hover:text-accent-hover font-semibold border-l border-hairline flex items-center gap-1.5 transition-colors disabled:opacity-50 touch-action-manipulation"
            title="Reset simulated states and sample overrides to baseline"
          >
            <RotateCcw size={12} className={resetMutation.isPending ? 'animate-spin' : ''} />
            Reset Demo
          </button>
        </div>

        {/* Circadian Theme Toggle: 44x44px ergonomic touch target */}
        <div className="flex items-center gap-1.5 pl-2">
          <button
            type="button"
            onClick={toggleTheme}
            title={theme === 'light' ? 'Switch to Dark Mode (Calibrated for Low Light)' : 'Switch to Light Mode'}
            aria-label="Toggle color theme"
            className="w-11 h-11 flex items-center justify-center rounded-xl text-muted hover:text-ink hover:bg-surface-elevated transition-colors focus-visible:outline-none touch-action-manipulation"
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>

          {/* User Profile Info */}
          <div className="hidden sm:flex items-center gap-2 px-2 py-1 bg-surface-elevated rounded-xl border border-hairline">
            <div className="w-7 h-7 rounded-lg bg-surface border border-hairline flex items-center justify-center">
              <User size={14} className="text-muted" />
            </div>
            <span className="text-xs font-medium text-ink pr-1">Analyst</span>
          </div>

          {/* Spatially isolated Log Out button: 44x44px target to prevent motor tremor error */}
          <button 
            type="button" 
            onClick={logout} 
            title="Log out of SupplyMind" 
            aria-label="Log out of SupplyMind"
            className="w-11 h-11 flex items-center justify-center rounded-xl text-muted hover:text-risk-high hover:bg-rose-500/10 transition-colors focus-visible:outline-none ml-1 touch-action-manipulation"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </header>
  );
}
export default Topbar;
