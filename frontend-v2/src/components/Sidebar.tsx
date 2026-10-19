import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  LayoutDashboard, ShieldAlert, List, Package, BrainCircuit, 
  ClipboardCheck, Settings, FileSpreadsheet, X, LogOut,
  SlidersHorizontal, ShoppingCart, AlertOctagon, Sparkles
} from 'lucide-react';

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const { logout } = useAuth();

  // Cognitive Chunking: Grouped into <= 5 items per chunk (Cowen 2001; Hick 1952)
  const navSections = [
    {
      label: 'Operations',
      items: [
        { name: 'Command Center', href: '/dashboard', icon: LayoutDashboard },
        { name: 'Inventory Heatmap', href: '/inventory', icon: Package },
        { name: 'Smart Reorders', href: '/reorder', icon: ShoppingCart },
        { name: 'Supplier Disruption', href: '/disruption', icon: AlertOctagon },
      ],
    },
    {
      label: 'Intelligence & Simulation',
      items: [
        { name: 'What-If Simulator', href: '/simulator', icon: SlidersHorizontal },
        { name: 'Ask SupplyMind', href: '/assistant', icon: Sparkles },
        { name: 'Model Observatory', href: '/models', icon: BrainCircuit },
      ],
    },
    {
      label: 'Governance & Audit',
      items: [
        { name: 'Override Console', href: '/override', icon: ShieldAlert },
        { name: 'Onboarding', href: '/onboarding', icon: ClipboardCheck },
        { name: 'Audit Log', href: '/audit', icon: List },
        { name: 'Reports', href: '/reports', icon: FileSpreadsheet },
        { name: 'Settings', href: '/settings', icon: Settings },
      ],
    },
  ];

  return (
    <aside className="w-64 bg-surface border-r border-hairline flex flex-col h-full shrink-0 relative select-none">
      {/* Mobile Close Button: Full 44x44px target (WCAG 2.5.5) */}
      <div className="absolute right-3 top-3 lg:hidden z-10">
        <button 
          onClick={onClose} 
          className="w-11 h-11 flex items-center justify-center rounded-xl bg-surface-elevated text-muted hover:text-ink hover:bg-surface border border-hairline transition-colors focus-visible:outline-none"
          title="Close Navigation"
          aria-label="Close Navigation"
        >
          <X size={18} />
        </button>
      </div>

      {/* Header Branding */}
      <div className="h-16 flex items-center px-5 border-b border-hairline shrink-0">
        <div className="w-9 h-9 rounded-xl bg-accent-indigo flex items-center justify-center mr-3 shadow-sm">
          <BrainCircuit size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-ink tracking-tight">SupplyMind</h1>
          <span className="text-[11px] text-muted font-medium">Risk Intelligence</span>
        </div>
      </div>

      {/* Navigation Groups */}
      <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto" aria-label="Main Navigation">
        {navSections.map((section) => (
          <div key={section.label} className="space-y-1">
            <h2 className="px-3 text-[10px] font-semibold font-mono tracking-wider text-muted uppercase">
              {section.label}
            </h2>
            <div className="space-y-0.5 pt-1">
              {section.items.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.href}
                  end={item.href === '/'}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 min-h-[44px] rounded-lg text-sm font-medium transition-colors touch-action-manipulation ${
                      isActive 
                        ? 'bg-surface-elevated text-ink border-l-4 border-accent-indigo font-semibold shadow-xs' 
                        : 'text-body hover:text-ink hover:bg-surface-elevated/60'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <item.icon 
                        size={18} 
                        className={`shrink-0 transition-colors ${isActive ? 'text-accent-indigo' : 'text-muted'}`} 
                        aria-hidden="true"
                      />
                      <span className="truncate">{item.name}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer User & Version Area */}
      <div className="p-3 border-t border-hairline flex flex-col gap-2 shrink-0">
        <button 
          onClick={logout}
          className="flex items-center gap-3 px-3 min-h-[44px] rounded-lg text-sm font-medium text-body hover:text-risk-high hover:bg-surface-elevated/60 transition-colors w-full text-left touch-action-manipulation"
          title="Sign Out of Session"
        >
          <LogOut size={18} className="text-muted shrink-0" aria-hidden="true" />
          <span>Sign Out</span>
        </button>
        <div className="text-xs text-muted flex justify-between px-3 pt-1">
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-risk-low animate-pulse" /> Live Node</span>
          <span className="font-mono text-[11px]">v1.4.2</span>
        </div>
      </div>
    </aside>
  );
}
