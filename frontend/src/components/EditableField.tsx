import { useState, useRef, useEffect } from "react";
import { Pencil, Check, X } from "lucide-react";
import { cn } from "../lib/utils";

interface Props {
  value: string;
  onSave: (value: string) => Promise<void>;
  multiline?: boolean;
  className?: string;
  displayClassName?: string;
}

export function EditableField({ value, onSave, multiline = false, className, displayClassName }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const ref = useRef<HTMLTextAreaElement & HTMLInputElement>(null);

  useEffect(() => {
    if (editing) {
      setDraft(value);
      setTimeout(() => ref.current?.focus(), 0);
    }
  }, [editing]);

  const handleSave = async () => {
    if (draft === value) { setEditing(false); return; }
    setSaving(true);
    try {
      await onSave(draft);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") { setEditing(false); setDraft(value); }
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSave();
  };

  if (editing) {
    return (
      <div className={cn("flex flex-col gap-1.5", className)}>
        {multiline ? (
          <textarea
            ref={ref as React.Ref<HTMLTextAreaElement>}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={Math.max(3, draft.split("\n").length)}
            className="w-full text-sm border border-brand-400 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none leading-relaxed"
          />
        ) : (
          <input
            ref={ref as React.Ref<HTMLInputElement>}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full text-sm font-semibold border border-brand-400 rounded-lg px-3 py-1.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        )}
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1 text-xs font-medium text-white bg-brand-600 hover:bg-brand-700 px-2.5 py-1 rounded-lg transition-colors disabled:opacity-50"
          >
            <Check className="w-3 h-3" />
            {saving ? "Saving..." : "Save"}
          </button>
          <button
            onClick={() => { setEditing(false); setDraft(value); }}
            className="flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-800 px-2.5 py-1 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-3 h-3" />
            Cancel
          </button>
          {multiline && (
            <span className="text-[10px] text-slate-400 ml-1">⌘Enter to save · Esc to cancel</span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn("group relative cursor-text", className)}
      onClick={() => setEditing(true)}
      title="Click to edit"
    >
      <span className={displayClassName}>{value}</span>
      <Pencil className="inline-block ml-1.5 w-3 h-3 text-slate-300 group-hover:text-brand-400 transition-colors align-middle" />
    </div>
  );
}
