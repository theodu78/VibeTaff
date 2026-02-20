interface StepProgressProps {
  step: number;
  maxSteps: number;
  label: string;
  toolIndex?: number;
  toolTotal?: number;
}

export default function StepProgress({
  step,
  maxSteps,
  label,
  toolIndex,
  toolTotal,
}: StepProgressProps) {
  const pct = Math.min((step / maxSteps) * 100, 100);

  return (
    <div className="my-2 text-xs">
      <div className="flex items-center justify-between mb-1">
        <span className="text-zinc-500 flex items-center gap-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse" />
          {label}
        </span>
        <span className="text-zinc-600">
          {step}/{maxSteps}
          {toolIndex && toolTotal && toolTotal > 1
            ? ` · ${toolIndex}/${toolTotal}`
            : ""}
        </span>
      </div>
      <div className="w-full h-0.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-zinc-500 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
