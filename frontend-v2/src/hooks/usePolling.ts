import { useEffect, useRef } from 'react';

type CallbackFunction = () => void | Promise<void>;

export function usePolling(callback: CallbackFunction, intervalMs: number) {
  const savedCallback = useRef<CallbackFunction | null>(null);

  // Remember the latest callback if it changes.
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Set up the interval.
  useEffect(() => {
    // Don't schedule if no interval is provided
    if (intervalMs === null) {
      return;
    }

    const tick = () => {
      if (savedCallback.current) {
        savedCallback.current();
      }
    };

    const id = setInterval(tick, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
}
