import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { Paperclip, ArrowUp, Square } from "lucide-react";
import "./Composer.css";

interface Props {
  disabled: boolean;
  sending: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
  onFiles: (files: FileList) => void;
  accept: string[];
  focusKey: string | null;
}

export function Composer({ disabled, sending, onSend, onStop, onFiles, accept, focusKey }: Props) {
  const [value, setValue] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  // Selecting or creating a thread should leave the user directly in the
  // message bar, ready to write the first prompt.
  useEffect(() => {
    if (!disabled && focusKey) taRef.current?.focus();
  }, [disabled, focusKey]);

  const submit = () => {
    if (!value.trim() || disabled || sending) return;
    onSend(value.trim());
    setValue("");
    if (taRef.current) taRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) onFiles(e.dataTransfer.files);
  };

  const autosize = () => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  return (
    <div
      className={`composer ${dragOver ? "composer-dragover" : ""} ${disabled ? "composer-disabled" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <button
        className="composer-attach"
        onClick={() => fileInputRef.current?.click()}
        disabled={disabled}
        aria-label="Attach files"
        type="button"
      >
        <Paperclip size={17} />
      </button>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={accept.join(",")}
        hidden
        onChange={(e) => {
          if (e.target.files?.length) onFiles(e.target.files);
          e.target.value = "";
        }}
      />

      <textarea
        ref={taRef}
        rows={1}
        placeholder={dragOver ? "Drop files to attach…" : "Ask about your document or use tools"}
        value={value}
        disabled={disabled}
        onChange={(e) => {
          setValue(e.target.value);
          autosize();
        }}
        onKeyDown={handleKeyDown}
      />

      {sending ? (
        <button className="composer-send composer-stop" onClick={onStop} aria-label="Stop generating">
          <Square size={13} fill="currentColor" />
        </button>
      ) : (
        <button
          className="composer-send"
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          <ArrowUp size={17} />
        </button>
      )}
    </div>
  );
}
