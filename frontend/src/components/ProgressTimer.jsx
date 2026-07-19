import { useEffect, useState } from "react";

// Wraps the existing .studio-loading/.spinner pattern with an elapsed-seconds
// counter (and optional step-label prefix), so a long AI action reads as "in
// progress" rather than a spinner that might have silently frozen.
export default function ProgressTimer({ label, steps, active = -1 }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    setElapsed(0);
    const id = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(id);
  }, [label]);

  const stepPrefix = steps && active >= 0 ? `${steps.slice(0, active + 1).join(" → ")} · ` : "";

  return (
    <div className="studio-loading">
      <span className="spinner" />
      {stepPrefix}{label} · {elapsed}s elapsed
    </div>
  );
}
