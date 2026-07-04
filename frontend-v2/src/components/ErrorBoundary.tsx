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
      return (
        <div className="flex flex-col items-center justify-center p-16 h-full w-full bg-canvas">
          <div className="w-16 h-16 rounded-full bg-surface-strong flex items-center justify-center mb-6">
            <ServerCrash className="text-semantic-down" size={32} />
          </div>
          <h2 className="text-2xl font-display text-ink mb-2">Connection failed</h2>
          <p className="text-body text-center max-w-md text-sm">
            The frontend could not retrieve data from the backend. Ensure the FastAPI server is running.
          </p>
          <div className="mt-6 p-4 bg-surface-soft border border-hairline rounded-xl max-w-2xl w-full overflow-auto">
            <pre className="text-xs text-semantic-down font-mono">
              {this.state.error?.toString()}
            </pre>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
