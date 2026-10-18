import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion, useScroll, useTransform } from 'framer-motion';
import { BrainCircuit, Activity, ShieldAlert, Cpu, Box, ChevronRight, CheckCircle2 } from 'lucide-react';

const AnimatedMarketingText = () => {
  const words = ['Automated', 'Resilient', 'Intelligent'];
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((current) => (current + 1) % words.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative inline-block h-[1.1em] overflow-hidden text-accent-indigo">
      {/* Hidden text to give the container the exact maximum width of all words */}
      <div className="invisible pointer-events-none flex flex-col">
        {words.map((w) => <span key={w}>{w}</span>)}
      </div>
      {words.map((word, i) => (
        <motion.span
          key={word}
          initial={{ y: 50, opacity: 0 }}
          animate={{
            y: i === index ? 0 : -50,
            opacity: i === index ? 1 : 0,
          }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="absolute left-0 top-0 w-full text-center"
        >
          {word}
        </motion.span>
      ))}
    </div>
  );
};

export function Landing() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { scrollY } = useScroll();
  const navBackground = useTransform(scrollY, [0, 50], ['rgba(0, 0, 0, 0)', 'rgba(15, 23, 42, 0.8)']);
  const navBorder = useTransform(scrollY, [0, 50], ['rgba(255, 255, 255, 0)', 'rgba(255, 255, 255, 0.1)']);
  const navBackdropBlur = useTransform(scrollY, [0, 50], ['blur(0px)', 'blur(12px)']);

  return (
    <div className="min-h-screen bg-canvas text-ink font-sans selection:bg-primary/30 scroll-smooth">

      {/* Floating Pill Navbar */}
      <motion.nav
        style={{
          backgroundColor: navBackground,
          borderColor: navBorder,
          backdropFilter: navBackdropBlur
        }}
        className="fixed top-6 left-1/2 -translate-x-1/2 z-50 w-[90%] max-w-5xl rounded-full border border-transparent px-6 py-3 flex items-center justify-between transition-shadow duration-300 shadow-2xl shadow-primary/5"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-accent-indigo flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <BrainCircuit size={16} className="text-white" />
          </div>
          <span className="font-bold text-ink tracking-tight">SupplyMind</span>
        </div>

        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-muted">
          <a href="#features" className="hover:text-ink transition-colors">Features</a>
          <a href="#architecture" className="hover:text-ink transition-colors">Architecture</a>
          <a href="#pricing" className="hover:text-ink transition-colors">Pricing</a>
          <a href="#docs" className="hover:text-ink transition-colors">Docs</a>
        </div>

        <div className="flex items-center gap-4">
          {isAuthenticated ? (
            <div className="magic-border">
              <button
                className="bg-ink text-canvas font-semibold px-5 py-2 text-sm rounded-full w-full shadow-lg shadow-primary/20 hover:opacity-90 transition-opacity"
                onClick={() => navigate('/dashboard')}
              >
                Command Center
              </button>
            </div>
          ) : (
            <div className="magic-border">
              <button
                className="bg-ink text-canvas font-semibold px-5 py-2 text-sm rounded-full w-full shadow-lg shadow-primary/20 hover:opacity-90 transition-opacity"
                onClick={() => navigate('/login')}
              >
                Sign In
              </button>
            </div>
          )}
        </div>
      </motion.nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-40 lg:pb-32 px-6 flex items-center justify-center min-h-[90vh]">
        <div className="relative w-full max-w-7xl">
          {/* Background Effects */}
          <div className="absolute inset-0 z-0">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/10 rounded-full blur-[140px] pointer-events-none mix-blend-screen" />
            <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCI+PHBhdGggZD0iTTAgMGgyNHYyNEgweiIgZmlsbD0ibm9uZSIvPjxwYXRoIGQ9Ik0wIDI0djBIMDBWMHoiIGZpbGw9Im5vbmUiLz48cGF0aCBkPSJNMCAyNHYwSDI0djB6IiBzdHJva2U9InJnYmEoMTUwLCAxNTAsIDE1MCwgMC4wNSkiIGZpbGw9Im5vbmUiLz48cGF0aCBkPSJNMCAwdjI0SDI0djB6IiBzdHJva2U9InJnYmEoMTUwLCAxNTAsIDE1MCwgMC4wNSkiIGZpbGw9Im5vbmUiLz48L3N2Zz4=')] opacity-40" />
            <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at center, transparent 0%, var(--canvas) 100%)' }} />
          </div>

          <div className="relative z-10 max-w-5xl mx-auto flex flex-col items-center text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-3 px-2 py-1.5 pr-4 rounded-full bg-surface/80 backdrop-blur-md border border-hairline text-xs font-medium text-muted mb-8 hover:bg-surface-elevated transition-colors shadow-sm"
            >
              <span className="px-2.5 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                Active
              </span>
              <span className="text-ink">OODA Agent v2.0 is now available</span>
              <ChevronRight className="w-3.5 h-3.5 ml-1 opacity-50" />
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="text-[3.5rem] sm:text-[5rem] md:text-[6rem] lg:text-[7.5rem] font-medium tracking-tighter text-ink mb-6 leading-[1.05] flex flex-col items-center"
            >
              <span>Supply Chain,</span>
              <AnimatedMarketingText />
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="text-muted text-lg md:text-xl lg:text-2xl leading-relaxed mb-12 max-w-3xl font-light"
            >
              Stop reacting to disruptions. OODA Agent predicts risks weeks in advance and autonomously executes mitigation strategies while you sleep.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-col sm:flex-row items-center gap-4 w-full justify-center"
            >
              <div className="magic-border w-full sm:w-auto">
                <button
                  className="bg-ink text-canvas font-semibold h-14 px-10 text-base rounded-full w-full transition-transform hover:scale-[1.02] active:scale-[0.98] shadow-xl shadow-primary/20"
                  onClick={() => navigate(isAuthenticated ? '/dashboard' : '/login')}
                >
                  {isAuthenticated ? 'Enter Command Center' : 'Get Started Free'}
                </button>
              </div>
              <button
                className="h-14 px-10 text-base rounded-full border border-hairline text-ink font-semibold transition-all hover:bg-surface hover:shadow-lg w-full sm:w-auto backdrop-blur-sm"
              >
                Book a Demo
              </button>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Social Proof / Logo Cloud */}
      <section className="py-12 border-y border-hairline bg-surface/30 overflow-hidden relative">
        <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-canvas to-transparent z-10" />
        <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-canvas to-transparent z-10" />
        <div className="flex whitespace-nowrap animate-marquee opacity-60 hover:opacity-100 transition-opacity">
          {[...Array(2)].map((_, j) => (
            <div key={j} className="flex items-center gap-16 mx-8">
              {['Acme Corp', 'Globex', 'Soylent', 'Initech', 'Umbrella', 'Massive Dynamic'].map((company, i) => (
                <div key={i} className="flex items-center gap-3 text-muted grayscale hover:grayscale-0 transition-all cursor-pointer">
                  <div className="w-8 h-8 bg-slate-800 rounded-md flex items-center justify-center">
                    <Box size={16} className="text-slate-400" />
                  </div>
                  <span className="text-xl font-bold tracking-tighter">{company}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* Bento Grid Features */}
      <section id="features" className="py-24 lg:py-32 px-6 max-w-7xl mx-auto">
        <div className="text-center max-w-3xl mx-auto mb-16 lg:mb-24">
          <h2 className="text-3xl lg:text-5xl font-bold tracking-tight mb-6">Built for Unpredictability</h2>
          <p className="text-lg text-muted">Legacy software tells you what happened yesterday. SupplyMind's neural networks tell you what will happen next week, and fixes it for you.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[320px]">
          {/* Large Feature 1 */}
          <div className="md:col-span-2 relative overflow-hidden rounded-[32px] bg-surface border border-hairline p-8 flex flex-col justify-end group hover:border-primary/50 transition-colors shadow-sm">
            <div className="absolute top-0 right-0 w-96 h-96 bg-accent-indigo/10 rounded-full blur-[100px] pointer-events-none group-hover:bg-accent-indigo/20 transition-colors" />
            <BrainCircuit className="absolute top-8 right-8 text-accent-indigo w-12 h-12 opacity-50" />
            <div className="relative z-10">
              <h3 className="text-2xl font-bold mb-3">OODA Agent Loop</h3>
              <p className="text-muted max-w-md">Our proprietary Observe, Orient, Decide, Act architecture autonomously resolves 73% of tier-1 supply chain disruptions without human intervention.</p>
            </div>
          </div>

          {/* Small Feature 1 */}
          <div className="relative overflow-hidden rounded-[32px] bg-surface border border-hairline p-8 flex flex-col justify-end group hover:border-risk-high/50 transition-colors shadow-sm">
            <div className="absolute top-0 right-0 w-64 h-64 bg-risk-high/10 rounded-full blur-[80px] pointer-events-none group-hover:bg-risk-high/20 transition-colors" />
            <ShieldAlert className="absolute top-8 right-8 text-risk-high w-10 h-10 opacity-50" />
            <div className="relative z-10">
              <h3 className="text-xl font-bold mb-3">Threat Detection</h3>
              <p className="text-muted text-sm">Monitor weather, geopolitics, and port congestion in real-time.</p>
            </div>
          </div>

          {/* Small Feature 2 */}
          <div className="relative overflow-hidden rounded-[32px] bg-surface border border-hairline p-8 flex flex-col justify-end group hover:border-accent-emerald/50 transition-colors shadow-sm">
            <div className="absolute top-0 right-0 w-64 h-64 bg-accent-emerald/10 rounded-full blur-[80px] pointer-events-none group-hover:bg-accent-emerald/20 transition-colors" />
            <Activity className="absolute top-8 right-8 text-accent-emerald w-10 h-10 opacity-50" />
            <div className="relative z-10">
              <h3 className="text-xl font-bold mb-3">Live Telemetry</h3>
              <p className="text-muted text-sm">Sub-second updates across your entire global logistics network.</p>
            </div>
          </div>

          {/* Large Feature 2 */}
          <div className="md:col-span-2 relative overflow-hidden rounded-[32px] bg-surface border border-hairline p-8 flex flex-col justify-end group hover:border-primary/50 transition-colors shadow-sm">
            <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 rounded-full blur-[100px] pointer-events-none group-hover:bg-primary/20 transition-colors" />
            <Cpu className="absolute top-8 right-8 text-primary w-12 h-12 opacity-50" />
            <div className="relative z-10">
              <h3 className="text-2xl font-bold mb-3">Predictive Digital Twin</h3>
              <p className="text-muted max-w-md">Simulate millions of scenarios instantly. Watch exactly how a single factory shutdown in Shenzhen ripples through your European inventory levels.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 lg:py-32 px-6">
        <div className="max-w-5xl mx-auto bg-surface-elevated border border-hairline rounded-[40px] p-12 lg:p-20 text-center relative overflow-hidden shadow-2xl">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCI+PHBhdGggZD0iTTAgMGgyNHYyNEgweiIgZmlsbD0ibm9uZSIvPjxwYXRoIGQ9Ik0wIDI0djBIMDBWMHoiIGZpbGw9Im5vbmUiLz48cGF0aCBkPSJNMCAyNHYwSDI0djB6IiBzdHJva2U9InJnYmEoMTUwLCAxNTAsIDE1MCwgMC4wNSkiIGZpbGw9Im5vbmUiLz48cGF0aCBkPSJNMCAwdjI0SDI0djB6IiBzdHJva2U9InJnYmEoMTUwLCAxNTAsIDE1MCwgMC4wNSkiIGZpbGw9Im5vbmUiLz48L3N2Zz4=')] opacity-20" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-accent-indigo/20 rounded-full blur-[120px] pointer-events-none" />

          <div className="relative z-10">
            <h2 className="text-4xl lg:text-6xl font-bold tracking-tight mb-6">Ready to upgrade your supply chain?</h2>
            <p className="text-xl text-muted mb-10 max-w-2xl mx-auto">Join industry leaders who have already replaced guesswork with autonomous intelligence.</p>

            <div className="flex flex-col sm:flex-row items-center gap-4 justify-center">
              <div className="magic-border w-full sm:w-auto">
                <button
                  className="bg-ink text-canvas font-semibold h-14 px-10 text-base rounded-full w-full shadow-lg shadow-primary/20 hover:opacity-90 transition-opacity"
                  onClick={() => navigate(isAuthenticated ? '/dashboard' : '/login')}
                >
                  {isAuthenticated ? 'Enter Command Center' : 'Start Free Trial'}
                </button>
              </div>
              <button className="h-14 px-10 text-base rounded-full border border-hairline font-semibold bg-surface text-ink hover:bg-canvas transition-colors w-full sm:w-auto">
                Talk to Sales
              </button>
            </div>

            <div className="mt-8 flex items-center justify-center gap-6 text-sm text-muted">
              <span className="flex items-center gap-2"><CheckCircle2 size={16} className="text-accent-emerald" /> No credit card required</span>
              <span className="flex items-center gap-2"><CheckCircle2 size={16} className="text-accent-emerald" /> 14-day free trial</span>
            </div>
          </div>
        </div>
      </section>

      {/* Simple Footer */}
      <footer className="py-8 border-t border-hairline text-center text-sm text-muted">
        <p>© 2026 SupplyMind. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default Landing;
