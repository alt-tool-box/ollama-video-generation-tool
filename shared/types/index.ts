export interface Job {
  id: string
  status: JobStatus
  original_prompt: string
  script?: Script
  created_at: string
  approved_at?: string
  completed_at?: string
  error_message?: string
  output_url?: string
  steps?: JobStep[]
}

export type JobStatus =
  | 'draft'
  | 'script_pending'
  | 'script_ready'
  | 'approved'
  | 'processing'
  | 'completed'
  | 'failed'

export interface Script {
  enhanced_prompt: string
  scenes: Scene[]
  total_duration: number
  style: string
}

export interface Scene {
  id: number
  description: string
  image_prompt: string
  duration_seconds: number
  narration: string
}

export interface JobStep {
  id: string
  job_id: string
  step_name: string
  status: StepStatus
  progress: number
  output_path?: string
  started_at?: string
  completed_at?: string
}

export type StepStatus = 'pending' | 'in_progress' | 'completed' | 'failed'

export interface ProgressUpdate {
  type: 'progress'
  job_id: string
  status: JobStatus
  step?: string
  progress?: number
  message?: string
  error?: string
}

export interface GenerateImageRequest {
  prompt: string
  job_id: string
  scene_id: number
  width?: number
  height?: number
  style?: string
}

export interface TTSRequest {
  text: string
  job_id: string
  scene_id: number
  voice?: string
  language?: string
}

export interface RenderVideoRequest {
  job_id: string
  frames: FrameData[]
  audio_path?: string
  fps?: number
  add_transitions?: boolean
}

export interface FrameData {
  image_path: string
  duration: number
  audio_path?: string
}
