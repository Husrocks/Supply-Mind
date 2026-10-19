import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { ServerCrash } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      const errorMsg = this.state.error?.message || this.state.error?.toString() || '';
      const isNetworkError =
        errorMsg.toLowerCase().includes('network error') ||
        errorMsg.toLowerCase().includes('failed to fetch') ||
        errorMsg.toLowerCase().includes('econnrefused') ||
        errorMsg.toLowerCase().includes('timeout');

      return (
        <div className="flex flex-col items-center justify-center p-8 sm:p-16 h-full w-full bg-canvas text-center">
          <div className="w-16 h-16 rounded-full bg-surface-strong flex items-center justify-center mb-6 border border-hairline shadow-lg">
            <ServerCrash className="text-risk-high" size={32} />
          </div>
          <h2 className="text-2xl font-display font-semibold text-ink mb-2">
            {isNetworkError ? 'Connection failed' : 'Rendering Error'}
          </h2>
          <p className="text-body text-center max-w-md text-sm mb-6">
            {isNetworkError
              ? 'The frontend could not retrieve data from the backend. Ensure the FastAPI server is running on http://127.0.0.1:8000.'
              : 'An unexpected runtime error occurred while rendering this view.'}
          </p>

          <div className="flex items-center gap-3 mb-6">
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="btn-primary !h-9 text-xs px-4"
            >
              Reload Page
            </button>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.href = '/';
              }}
              className="btn-secondary !h-9 text-xs px-4"
            >
              Return to Dashboard
            </button>
          </div>

          <div className="mt-2 p-4 bg-surface-soft border border-hairline rounded-xl max-w-2xl w-full text-left overflow-auto">
            <div className="text-[10px] text-muted font-mono uppercase mb-1">Error Diagnostic</div>
            <pre className="text-xs text-rose-400 font-mono whitespace-pre-wrap break-all">
              {this.state.error?.stack || this.state.error?.toString()}
            </pre>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
