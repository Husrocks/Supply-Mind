import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import clsx from 'clsx';

export function Layout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-screen bg-canvas text-ink overflow-hidden relative">
      {/* Responsive Sidebar Container */}
      <div className={clsx(
        "fixed lg:static top-0 bottom-0 left-0 z-45 transition-transform duration-300 lg:translate-x-0 h-full",
        isSidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <Sidebar onClose={() => setIsSidebarOpen(false)} />
      </div>

      {/* Backdrop for Mobile Drawer */}
      {isSidebarOpen && (
        <div 
          onClick={() => setIsSidebarOpen(false)}
          className="fixed inset-0 bg-black/60 z-40 lg:hidden cursor-pointer backdrop-blur-xs transition-opacity"
        />
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Topbar onToggleSidebar={() => setIsSidebarOpen(true)} />
        <main className="flex-1 overflow-hidden bg-canvas">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
export default Layout;
