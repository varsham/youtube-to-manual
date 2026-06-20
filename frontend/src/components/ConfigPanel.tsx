import { Select } from "./ui/select";
import { Textarea } from "./ui/textarea";
import { Card, CardHeader, CardContent } from "./ui/card";
import { Settings } from "lucide-react";
import type { UserConfig, ExperienceLevel, ExplanationStyle, CheckpointFrequency } from "../types";

interface Props {
  config: UserConfig;
  onChange: (config: UserConfig) => void;
  disabled?: boolean;
}

export function ConfigPanel({ config, onChange, disabled }: Props) {
  const set = <K extends keyof UserConfig>(key: K, value: UserConfig[K]) =>
    onChange({ ...config, [key]: value });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-slate-500" />
          <h3 className="font-semibold text-slate-800 text-sm">User Profile</h3>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Experience Level
          </label>
          <Select
            value={config.experience_level}
            onChange={(e) => set("experience_level", e.target.value as ExperienceLevel)}
            disabled={disabled}
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="expert">Expert</option>
          </Select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Explanation Style
          </label>
          <Select
            value={config.explanation_style}
            onChange={(e) => set("explanation_style", e.target.value as ExplanationStyle)}
            disabled={disabled}
          >
            <option value="simple">Simple</option>
            <option value="detailed">Detailed</option>
            <option value="technical">Technical</option>
            <option value="analogies">With Analogies</option>
          </Select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Checkpoint Frequency
          </label>
          <Select
            value={config.checkpoint_frequency}
            onChange={(e) => set("checkpoint_frequency", e.target.value as CheckpointFrequency)}
            disabled={disabled}
          >
            <option value="low">Low (every 3 steps)</option>
            <option value="medium">Medium (every step)</option>
            <option value="high">High (every step + sub-steps)</option>
          </Select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Your Background{" "}
            <span className="text-slate-400 font-normal">(optional)</span>
          </label>
          <Textarea
            value={config.user_skills}
            onChange={(e) => set("user_skills", e.target.value)}
            placeholder="e.g. I know Python but am new to machine learning..."
            rows={3}
            disabled={disabled}
          />
        </div>
      </CardContent>
    </Card>
  );
}
