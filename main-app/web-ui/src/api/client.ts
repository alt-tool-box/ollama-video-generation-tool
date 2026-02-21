import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Job {
  id: string
  status: string
  original_prompt: string
  script?: Script
  created_at: string
  approved_at?: string
  completed_at?: string
  error_message?: string
  output_url?: string
  steps?: JobStep[]
}

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
  step_name: string
  status: string
  progress: number
}

export const createJob = async (prompt: string): Promise<Job> => {
  const response = await api.post('/jobs', { prompt })
  return response.data
}

export const getJobs = async (): Promise<Job[]> => {
  const response = await api.get('/jobs')
  return response.data
}

export const getJob = async (jobId: string): Promise<Job> => {
  const response = await api.get(`/jobs/${jobId}`)
  return response.data
}

export const deleteJob = async (jobId: string): Promise<void> => {
  await api.delete(`/jobs/${jobId}`)
}

export const generateScript = async (jobId: string): Promise<void> => {
  await api.post(`/jobs/${jobId}/generate-script`)
}

export const updateScript = async (jobId: string, script: Partial<Script>): Promise<Script> => {
  const response = await api.put(`/jobs/${jobId}/script`, script)
  return response.data.script
}

export const regenerateScene = async (jobId: string, sceneId: number, feedback?: string): Promise<Scene> => {
  const response = await api.post(`/jobs/${jobId}/regenerate-scene`, {
    scene_id: sceneId,
    feedback,
  })
  return response.data.scene
}

export const approveAndGenerate = async (jobId: string): Promise<void> => {
  await api.post(`/jobs/${jobId}/approve`)
}

export const retryJob = async (jobId: string): Promise<{ message: string; job_id: string }> => {
  const response = await api.post(`/jobs/${jobId}/retry`)
  return response.data
}

export const resetJob = async (jobId: string): Promise<{ success: boolean; job_id: string }> => {
  const response = await api.post(`/jobs/${jobId}/reset`)
  return response.data
}

export default api
