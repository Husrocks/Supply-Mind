import { useEffect, useState, useRef } from 'react';
import { X, Terminal, Loader2 } from 'lucide-react';
import { getRetrainLogsUrl } from '../../api/client';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';

interface RetrainLogsModalProps {
  jobId: number | null;
  modelName: string;
  onClose: () => void;
}

export function RetrainLogsModal({ jobId, modelName, onClose }: RetrainLogsModalProps) {
  const [logs, setLogs] = useState<string>('');
  const [status, setStatus] = useState<'connecting' | 'connected' | 'error' | 'done'>('connecting');
  const bottomRef = useRef<HTMLDivElement>(null);
  const reduced = usePrefersReducedMotion();

  useEffect(() => {
    if (jobId === null) return;
    
    setLogs('');
    setStatus('connecting');
    const url = getRetrainLogsUrl(jobId);
    
    let abortController = new AbortController();
    
    const fetchStream = async () => {
      try {
        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('supplymind_token')}`
          },
          signal: abortController.signal
        });
        
        if (!response.ok) {
          throw new Error(`Failed to fetch logs: ${response.status}`);
        }
        
        setStatus('connected');
        
        if (!response.body) {
          throw new Error('ReadableStream not supported');
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            setStatus('done');
            break;
          }
          if (value) {
            setLogs(prev => prev + decoder.decode(value, { stream: true }));
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        setStatus('error');
        setLogs(prev => prev + `\n\n[ERROR] ${err.message}`);
      }
    };
    
    fetchStream();
    
    return () => {
      abortController.abort();
    };
  }, [jobId]);

  useEffect(() => {
    if (!reduced) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    } else {
      bottomRef.current?.scrollIntoView();
    }
  }, [logs, reduced]);

  if (jobId === null) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div 
        className="bg-[#0f172a] border border-slate-700/50 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden"
        style={{
          boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 24px 48px rgba(0,0,0,0.5)'
        }}
      >
        <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="bg-slate-800 p-2 rounded-lg">
              <Terminal size={18} className="text-indigo-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-200 leading-tight">Job #{jobId} Logs</h2>
              <p className="text-xs text-slate-400 mt-0.5">{modelName} Retraining</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              {status === 'connecting' && <Loader2 size={14} className="text-slate-400 animate-spin" />}
              {status === 'connected' && <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />}
              {status === 'done' && <span className="w-2 h-2 rounded-full bg-slate-500" />}
              {status === 'error' && <span className="w-2 h-2 rounded-full bg-rose-500" />}
              
              <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
                {status}
              </span>
            </div>
            
            <button 
              onClick={onClose}
              className="p-2 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>
        
        <div className="flex-1 p-4 bg-[#020617] overflow-y-auto font-mono text-[11px] sm:text-xs text-slate-300 leading-relaxed custom-scrollbar whitespace-pre-wrap">
          {logs || (status === 'connecting' ? 'Connecting to log stream...' : 'No logs available.')}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
