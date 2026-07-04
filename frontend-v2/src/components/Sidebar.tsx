import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, ShieldAlert, List, Package, BrainCircuit, 
  ClipboardCheck, Settings, FileSpreadsheet, X 
} from 'lucide-react';

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const navigation = [
    { name: 'Command Center', href: '/', icon: LayoutDashboard },
    { name: 'Override Console', href: '/override', icon: ShieldAlert },
    { name: 'Onboarding', href: '/onboarding', icon: ClipboardCheck },
    { name: 'Audit Log', href: '/audit', icon: List },
    { name: 'Inventory Heatmap', href: '/inventory', icon: Package },
    { name: 'Model Observatory', href: '/models', icon: BrainCircuit },
    { name: 'Reports', href: '/reports', icon: FileSpreadsheet },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-60 bg-slate-950/90 border-r border-hairline flex flex-col h-full shrink-0 backdrop-blur-md relative">
      {/* Mobile Close Button */}
      <div className="absolute right-4 top-4 lg:hidden">
        <button 
          onClick={onClose} 
          className="p-1.5 rounded-full bg-slate-900/80 text-muted hover:text-ink hover:bg-slate-800 transition-colors focus:ring-1 focus:ring-accent-indigo focus:outline-none"
          title="Close Navigation"
        >
          <X size={16} />
        </button>
      </div>

      <div className="h-16 flex items-center px-5 border-b border-hairline shrink-0">
        <div className="w-8 h-8 rounded-full bg-accent-indigo flex items-center justify-center mr-3">
          <BrainCircuit size={16} className="text-white" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-ink">SupplyMind</h1>
          <span className="text-[10px] text-muted">Risk Intelligence</span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            end={item.href === '/'}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                isActive ? 'bg-slate-800/80 text-ink' : 'text-body hover:text-ink hover:bg-slate-800/40'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <item.icon size={17} className={isActive ? 'text-accent-indigo' : 'text-muted'} />
                <span className="truncate">{item.name}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-hairline text-xs text-muted flex justify-between shrink-0">
        <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-risk-low" /> Online</span>
        <span className="font-mono">v1.4</span>
      </div>
    </aside>
  );
}
