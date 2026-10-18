import { useActionState, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { BrainCircuit, Loader2, ArrowLeft } from 'lucide-react';
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
          navigate('/'); // Redirect to Landing Page Hero
          return { error: null, success: true };
        } else {
          throw new Error('No token received');
        }
      } catch (error: any) {
        const errorMsg = error.response ? (error.response.data?.detail || 'Invalid credentials') : 'Network error: Backend is unreachable. Please ensure it is running.';
        toast.error(errorMsg);
        return { error: errorMsg };
      }
    },
    null
  );

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background matches Landing */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/10 rounded-full blur-[140px] pointer-events-none mix-blend-screen" />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCI+PHBhdGggZD0iTTAgMGgyNHYyNEgweiIgZmlsbD0ibm9uZSIvPjxwYXRoIGQ9Ik0wIDI0djBIMDBWMHoiIGZpbGw9Im5vbmUiLz48cGF0aCBkPSJNMCAyNHYwSDI0djB6IiBzdHJva2U9InJnYmEoMTUwLCAxNTAsIDE1MCwgMC4wNSkiIGZpbGw9Im5vbmUiLz48cGF0aCBkPSJNMCAwdjI0SDI0djB6IiBzdHJva2U9InJnYmEoMTUwLCAxNTAsIDE1MCwgMC4wNSkiIGZpbGw9Im5vbmUiLz48L3N2Zz4=')] opacity-60" />
        <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at center, transparent 0%, var(--canvas) 100%)' }} />
      </div>

      {/* Back button */}
      <button 
        onClick={() => navigate('/')}
        className="absolute top-8 left-8 z-20 flex items-center gap-2 text-sm font-medium text-muted hover:text-ink transition-colors"
      >
        <ArrowLeft size={16} />
        Back to Home
      </button>

      {/* Login Card */}
      <div className="relative z-10 w-full max-w-[400px]">
        <div className="bg-surface border border-hairline rounded-[24px] p-6 sm:p-8 shadow-2xl shadow-primary/5 backdrop-blur-sm">
          <div className="flex flex-col items-center text-center mb-6">
            <div className="w-12 h-12 rounded-[14px] bg-accent-indigo flex items-center justify-center shadow-lg shadow-indigo-500/20 mb-4">
              <BrainCircuit size={24} className="text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-ink">Welcome back</h1>
            <p className="text-xs text-muted mt-1">Sign in to your Command Center</p>
          </div>

          <form action={formAction} className="space-y-5">
            <div className="space-y-4">
              <div>
                <label className="text-[11px] font-semibold text-body block mb-1.5 uppercase tracking-wide">Email Address</label>
                <input 
                  type="email" 
                  name="email" 
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-11 px-4 rounded-xl bg-canvas border border-hairline text-ink text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all shadow-sm" 
                  placeholder="admin@supplymind.ai"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-body block mb-1.5 uppercase tracking-wide">Password</label>
                <input 
                  type="password" 
                  name="password" 
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-11 px-4 rounded-xl bg-canvas border border-hairline text-ink text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all shadow-sm" 
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="rounded border-hairline bg-canvas text-primary focus:ring-primary/50 focus:ring-offset-0" />
                <span className="text-[11px] font-medium text-muted">Remember me</span>
              </label>
              <a href="#" className="text-[11px] font-semibold text-accent-indigo hover:text-indigo-400 transition-colors">
                Forgot password?
              </a>
            </div>

            <div className="pt-2">
              <button type="submit" disabled={isPending} className="btn-primary w-full h-11 text-sm shadow-lg shadow-primary/20 rounded-xl transition-transform hover:scale-[1.02] active:scale-[0.98]">
                {isPending ? <Loader2 className="animate-spin mx-auto" size={18} /> : 'Sign In'}
              </button>
              
              <button
                type="button"
                onClick={() => {
                  setEmail('admin@supplymind.ai');
                  setPassword('admin');
                }}
                className="w-full text-[11px] font-medium text-muted hover:text-ink mt-2 py-2 transition-colors rounded-xl"
              >
                Fill Demo Credentials
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Login;
