import { cn } from "../../lib/utils";

interface ProgressProps {
  value: number;
  className?: string;
  showLabel?: boolean;
}

export function Progress({ value, className, showLabel }: ProgressProps) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("w-full", className)}>
      <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
        <div
          className="h-full bg-brand-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <p className="text-xs text-slate-500 mt-1 text-right">{Math.round(pct)}%</p>
      )}
    </div>
  );
}
