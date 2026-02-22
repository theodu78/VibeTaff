interface StepIndicatorProps {
  step: number;
  maxSteps: number;
  label?: string;
}

export default function StepIndicator({ step, maxSteps, label }: StepIndicatorProps) {
  const pct = Math.min(100, (step / maxSteps) * 100);

  const barColor =
    pct < 50
      ? "bg-emerald-500"
      : pct < 80
      ? "bg-amber-500"
      : "bg-red-500";

  const textColor =
    pct < 50
      ? "text-emerald-400"
      : pct < 80
      ? "text-amber-400"
      : "text-red-400";

  return (
    <div className="flex items-center gap-2 text-[11px] text-zinc-500">
      <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden max-w-[120px]">
        <div
          className={`h-full rounded-full transition-all duration-300 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={textColor}>
        {step}/{maxSteps}
      </span>
      {label && (
        <span className="text-zinc-600 truncate max-w-[200px]">{label}</span>
      )}
    </div>
  );
}
