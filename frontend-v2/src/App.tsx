import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { Toaster } from 'react-hot-toast';
import { Layout } from './components/Layout';
import { Login } from './views/Login';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ViewSkeleton } from './components/ui/ViewSkeleton';
import { usePrefersReducedMotion } from './hooks/usePrefersReducedMotion';
import { ErrorBoundary } from './components/ErrorBoundary';

const NetworkDashboard = lazy(() => import('./views/NetworkDashboard'));
const OverrideConsole = lazy(() => import('./views/OverrideConsole'));
const AuditLog = lazy(() => import('./views/AuditLog'));
const InventoryHeatmap = lazy(() => import('./views/InventoryHeatmap'));
const ModelObservatory = lazy(() => import('./views/ModelObservatory'));
const SupplierOnboarding = lazy(() => import('./views/SupplierOnboarding'));
const Settings = lazy(() => import('./views/Settings'));
const SupplierDetail = lazy(() => import('./views/SupplierDetail'));
const SkuDetail = lazy(() => import('./views/SkuDetail'));
const Reports = lazy(() => import('./views/Reports'));
const NotFound = lazy(() => import('./views/NotFound'));

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}

function Lazy({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<ViewSkeleton />}>{children}</Suspense>
    </ErrorBoundary>
  );
}

function AnimatedOutlet() {
  const location = useLocation();
  const reduced = usePrefersReducedMotion();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={reduced ? false : { opacity: 0, x: 6 }}
        animate={{ opacity: 1, x: 0 }}
        exit={reduced ? undefined : { opacity: 0, x: -6 }}
        transition={{ duration: 0.17 }}
        className="h-full"
      >
        <Outlet />
      </motion.div>
    </AnimatePresence>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Toaster position="top-right" toastOptions={{
            style: { background: 'rgba(15,23,42,0.92)', color: '#f1f5f9', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '12px' },
          }} />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route element={<AnimatedOutlet />}>
                <Route index element={<Lazy><NetworkDashboard /></Lazy>} />
                <Route path="override" element={<Lazy><OverrideConsole /></Lazy>} />
                <Route path="onboarding" element={<Lazy><SupplierOnboarding /></Lazy>} />
                <Route path="audit" element={<Lazy><AuditLog /></Lazy>} />
                <Route path="inventory" element={<Lazy><InventoryHeatmap /></Lazy>} />
                <Route path="models" element={<Lazy><ModelObservatory /></Lazy>} />
                <Route path="settings" element={<Lazy><Settings /></Lazy>} />
                <Route path="supplier/:supplier_id" element={<Lazy><SupplierDetail /></Lazy>} />
                <Route path="sku/:sku_id" element={<Lazy><SkuDetail /></Lazy>} />
                <Route path="reports" element={<Lazy><Reports /></Lazy>} />
                <Route path="*" element={<Lazy><NotFound /></Lazy>} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
