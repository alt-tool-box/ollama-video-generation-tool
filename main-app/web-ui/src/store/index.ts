import { create } from 'zustand'
import { Job } from '../api/client'

interface ProgressState {
  step: string
  progress: number
  message?: string
}

interface AppState {
  currentJob: Job | null
  jobProgress: Record<string, ProgressState>
  jobStatus: Record<string, string>
  
  setCurrentJob: (job: Job | null) => void
  updateJobProgress: (jobId: string, step: string, progress: number, message?: string) => void
  setJobStatus: (jobId: string, status: string) => void
  clearProgress: (jobId: string) => void
}

export const useStore = create<AppState>((set) => ({
  currentJob: null,
  jobProgress: {},
  jobStatus: {},
  
  setCurrentJob: (job) => set({ currentJob: job }),
  
  updateJobProgress: (jobId, step, progress, message) => 
    set((state) => ({
      jobProgress: {
        ...state.jobProgress,
        [jobId]: { step, progress, message }
      }
    })),
  
  setJobStatus: (jobId, status) =>
    set((state) => ({
      jobStatus: {
        ...state.jobStatus,
        [jobId]: status
      }
    })),
  
  clearProgress: (jobId) =>
    set((state) => {
      const { [jobId]: _, ...rest } = state.jobProgress
      return { jobProgress: rest }
    }),
}))
