export function ViewSkeleton() {
  return (
    <div className="p-6 lg:p-8 space-y-5 animate-pulse">
      <div className="h-8 w-64 bg-slate-800 rounded-lg" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="glass-card h-28 bg-slate-800/40" />
        ))}
      </div>
      <div className="glass-card h-80 bg-slate-800/40" />
    </div>
  );
}
