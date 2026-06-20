export type ExperienceLevel = "beginner" | "intermediate" | "expert";
export type ExplanationStyle = "simple" | "detailed" | "technical" | "analogies";
export type CheckpointFrequency = "low" | "medium" | "high";
export type JobStatus =
  | "pending"
  | "downloading"
  | "extracting_frames"
  | "segmenting"
  | "generating"
  | "complete"
  | "failed";
export type CorrectionStatus = "none" | "suggested" | "approved" | "rejected";

export interface UserConfig {
  experience_level: ExperienceLevel;
  explanation_style: ExplanationStyle;
  checkpoint_frequency: CheckpointFrequency;
  screenshots_per_step: number;
  user_skills: string;
}

export interface Job {
  id: string;
  youtube_url: string;
  status: JobStatus;
  video_title: string | null;
  video_duration: number | null;
  video_thumbnail: string | null;
  total_steps: number;
  progress: number;
  log_messages: string[];
  error_message: string | null;
  config: UserConfig;
  created_at: string;
}

export interface Step {
  id: string;
  order: number;
  title: string;
  explanation: string;
  checkpoint: string;
  before_frame_id: string | null;
  after_frame_id: string | null;
  before_frame_url: string | null;
  after_frame_url: string | null;
  segment_start: number | null;
  segment_end: number | null;
  correction_status: CorrectionStatus;
  correction_suggestion: CorrectionSuggestion | null;
  candidate_before_frames: string[];
  candidate_after_frames: string[];
  updated_at: string | null;
}

export interface CorrectionSuggestion {
  step_id?: string;
  issue_type?: string;
  description?: string;
  proposed_action?: "split" | "merge" | "rewrite" | string;
  proposed_detail?: string;
  message?: string;
}

export type RewriteInstruction =
  | "simpler"
  | "detailed"
  | "technical"
  | "analogies"
  | string;
