export function ProgressBar({ value }: { value: number }) {
  const bounded = Math.max(0, Math.min(100, value));
  return (
    <div className="progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={bounded}>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${bounded}%` }} />
      </div>
      <div className="progress-value">{bounded}%</div>
    </div>
  );
}
