import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { LogOut, User, Activity, Menu, Sun, Moon } from 'lucide-react';

interface TopbarProps {
  onToggleSidebar?: () => void;
}

export function Topbar({ onToggleSidebar }: TopbarProps) {
  const { logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const title: Record<string, string> = {
    '/': 'Command Center',
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

  return (
    <header className="h-16 border-b border-hairline bg-surface flex items-center justify-between px-6 shrink-0 z-30">
      <div className="flex items-center gap-3">
        {/* Hamburger Menu Toggle */}
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-2 rounded-xl bg-surface-elevated border border-hairline text-body hover:text-ink hover:bg-surface transition-colors focus:ring-1 focus:ring-primary focus:outline-none"
          title="Toggle Navigation Menu"
        >
          <Menu size={18} />
        </button>

        <h2 className="text-base font-semibold text-ink">{getPageTitle()}</h2>
        <span className="hidden sm:flex items-center gap-1 text-[10px] text-muted bg-surface-elevated px-2.5 py-1 rounded-full border border-hairline">
          <Activity size={10} className="text-primary" /> Live
        </span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 border-l border-hairline pl-4">
          <button
            type="button"
            onClick={toggleTheme}
            title="Toggle color theme"
            className="p-2 rounded-full text-muted hover:text-ink hover:bg-surface-elevated transition-colors focus:ring-1 focus:ring-primary focus:outline-none"
          >
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
          </button>
          <div className="w-8 h-8 rounded-full bg-surface-elevated border border-hairline flex items-center justify-center">
            <User size={15} className="text-muted" />
          </div>
          <button 
            type="button" 
            onClick={logout} 
            title="Log out" 
            className="p-2 rounded-full text-muted hover:text-risk-high transition-colors focus:ring-1 focus:ring-risk-high focus:outline-none"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </header>
  );
}
export default Topbar;
