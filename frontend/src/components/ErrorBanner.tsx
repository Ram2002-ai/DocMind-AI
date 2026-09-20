import { AlertCircle, X } from "lucide-react";
import "./ErrorBanner.css";

export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="error-banner" role="alert">
      <AlertCircle size={14} />
      <span>{message}</span>
      <button onClick={onDismiss} aria-label="Dismiss">
        <X size={13} />
      </button>
    </div>
  );
}
