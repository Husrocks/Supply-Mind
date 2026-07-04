import { useActionState, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { BrainCircuit, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [_, formAction, isPending] = useActionState(
    async (_prevState: any, formData: FormData) => {
      const emailValue = formData.get('email') as string;
      const passwordValue = formData.get('password') as string;

      try {
        const params = new URLSearchParams();
        params.append('username', emailValue);
        params.append('password', passwordValue);
        const response = await apiClient.post('/auth/login', params, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
        const { access_token } = response.data;
        if (access_token) {
          login(access_token);
          toast.success('Authentication successful');
          navigate('/');
          return { error: null, success: true };
        } else {
          throw new Error('No token received');
        }
      } catch (error: any) {
        const errorMsg = error.response?.data?.detail || 'Invalid credentials';
        toast.error(errorMsg);
        return { error: errorMsg };
      }
    },
    null
  );

  return (
    <div className="min-h-screen bg-canvas flex">
      {/* Left side - Hero Image & Branding */}
      <div className="hidden lg:flex w-1/2 relative bg-slate-900 border-r border-hairline overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img 
            src="/hero.png" 
            alt="AI-generated supply chain hero" 
            className="w-full h-full object-cover opacity-60 mix-blend-luminosity"
            onError={(e) => {
              // Fallback if artifacts path doesn't map directly in dev server
              (e.target as HTMLImageElement).src = "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?q=80&w=2070&auto=format&fit=crop";
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-canvas via-canvas/40 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-canvas/80 to-transparent" />
        </div>
        
        <div className="relative z-10 p-12 flex flex-col h-full justify-between w-full max-w-2xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-accent-indigo flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <BrainCircuit size={24} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">SupplyMind</h1>
          </div>

          <div className="mb-12 space-y-6">
            <h2 className="text-4xl font-bold text-white leading-tight">
              AI-driven Resilience for Modern Supply Chains
            </h2>
            <p className="text-lg text-slate-300 leading-relaxed max-w-lg">
              Predict disruptions, optimize inventory, and automate risk mitigation with cutting-edge autonomous agents and time-series forecasting.
            </p>
            <div className="flex items-center gap-4 pt-4">
              <div className="flex -space-x-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="w-10 h-10 rounded-full border-2 border-canvas bg-slate-800" />
                ))}
              </div>
              <p className="text-sm text-slate-400 font-medium">Trusted by leading enterprises</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm space-y-8">
          <div className="text-center lg:text-left space-y-2">
            <h2 className="text-2xl font-bold text-ink">Welcome back</h2>
            <p className="text-sm text-body">Sign in to your Command Center</p>
          </div>

          <form action={formAction} className="space-y-5">
            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-body block mb-2">Email Address</label>
                <input 
                  type="email" 
                  name="email" 
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-12 px-4 rounded-xl bg-slate-900/40 border border-hairline text-ink text-sm outline-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner" 
                  placeholder="admin@supplymind.ai"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-body block mb-2">Password</label>
                <input 
                  type="password" 
                  name="password" 
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-12 px-4 rounded-xl bg-slate-900/40 border border-hairline text-ink text-sm outline-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner" 
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="rounded border-hairline bg-slate-900/60 text-primary focus:ring-primary/50 focus:ring-offset-0" />
                <span className="text-xs text-muted">Remember me</span>
              </label>
              <a href="#" className="text-xs font-medium text-accent-indigo hover:text-indigo-400 transition-colors">
                Forgot password?
              </a>
            </div>

            <button type="submit" disabled={isPending} className="btn-primary w-full !h-12 text-sm shadow-lg shadow-indigo-500/20">
              {isPending ? <Loader2 className="animate-spin mx-auto" size={18} /> : 'Sign In'}
            </button>
            
            <button
              type="button"
              onClick={() => {
                setEmail('admin@supplymind.ai');
                setPassword('admin');
              }}
              className="w-full text-xs font-medium text-slate-400 hover:text-ink mt-4 py-2 transition-colors border border-transparent hover:border-hairline rounded-lg"
            >
              Fill Demo Credentials
            </button>
          </form>
          
          <p className="text-center text-xs text-muted">
            Don't have an account? <a href="#" className="font-medium text-accent-indigo hover:text-indigo-400 transition-colors">Request access</a>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;
