import { useState, FormEvent } from "react";
import { Youtube } from "lucide-react";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import type { UserConfig } from "../types";

interface Props {
  onSubmit: (url: string, config: UserConfig) => void;
  loading: boolean;
  defaultConfig: UserConfig;
}

export function URLInput({ onSubmit, loading, defaultConfig }: Props) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setError("Please enter a YouTube URL");
      return;
    }
    if (!trimmed.includes("youtube.com") && !trimmed.includes("youtu.be")) {
      setError("Must be a YouTube URL (youtube.com or youtu.be)");
      return;
    }
    setError("");
    onSubmit(trimmed, defaultConfig);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Youtube
            className="absolute left-3 top-1/2 -translate-y-1/2 text-red-500 w-4 h-4"
          />
          <Input
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              if (error) setError("");
            }}
            className="pl-9"
            disabled={loading}
          />
        </div>
        <Button type="submit" loading={loading} disabled={!url.trim()}>
          Convert
        </Button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </form>
  );
}
