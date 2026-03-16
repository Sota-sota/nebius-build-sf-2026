import { create } from "zustand"

export const useAppStore = create((set, get) => ({
  // Connection
  connected: false,
  setConnected: (connected) => set({ connected }),

  // Camera
  cameraFrame: null,
  setCameraFrame: (cameraFrame) => set({ cameraFrame }),

  // Scene perception
  scene: null,
  setScene: (scene) => set({ scene }),

  // Reasoning timeline
  reasoningSteps: [],
  addReasoningStep: (step) =>
    set((s) => ({ reasoningSteps: [...s.reasoningSteps, step] })),
  clearReasoningSteps: () => set({ reasoningSteps: [] }),

  // Tavily search results
  tavilyResults: [],
  addTavilyResult: (result) =>
    set((s) => ({ tavilyResults: [...s.tavilyResults, result] })),
  clearTavilyResults: () => set({ tavilyResults: [] }),

  // Action plan
  actionPlan: null,
  setActionPlan: (actionPlan) => set({ actionPlan }),

  // Pending approval
  pendingApproval: null,
  setPendingApproval: (pendingApproval) => set({ pendingApproval }),

  // Arm status
  armStatus: null,
  setArmStatus: (armStatus) => set({ armStatus }),

  // Command history
  commandHistory: [],
  addCommand: (text) =>
    set((s) => ({
      commandHistory: [
        { text, timestamp: new Date().toISOString() },
        ...s.commandHistory,
      ].slice(0, 20),
    })),

  // Toloka HomER demos
  homerResults: [],
  addHomerResult: (result) =>
    set((s) => ({ homerResults: [...s.homerResults, result] })),
  clearHomerResults: () => set({ homerResults: [] }),

  // Toloka security eval
  securityEval: null, // {status, total, completed, passed, failed, score, results, message}
  setSecurityEval: (securityEval) => set({ securityEval }),

  // Pipeline status
  pipelineStatus: "idle", // idle | perceiving | searching | planning | awaiting_approval | executing | completed | error
  setPipelineStatus: (pipelineStatus) => set({ pipelineStatus }),

  // Handle incoming WebSocket event
  handleEvent: (event) => {
    const { type, data, timestamp } = event

    switch (type) {
      case "camera_frame":
        get().setCameraFrame(data)
        break

      case "perception_result":
        get().setScene({ ...data, timestamp })
        get().addReasoningStep({
          step: "perceiving",
          detail: `Detected ${data.objects?.length || 0} objects`,
          timestamp,
          data,
        })
        get().setPipelineStatus("perceiving")
        break

      case "reasoning_step":
        get().addReasoningStep({
          step: data.step,
          detail: data.detail,
          tavily_query: data.tavily_query,
          timestamp,
        })
        get().setPipelineStatus(data.step)
        break

      case "tavily_result":
        get().addTavilyResult({ ...data, timestamp })
        break

      case "action_plan":
        get().setActionPlan(data)
        if (data.requires_approval) {
          get().setPendingApproval(data)
          get().setPipelineStatus("awaiting_approval")
        } else {
          get().setPipelineStatus("executing")
        }
        get().addReasoningStep({
          step: data.requires_approval ? "awaiting_approval" : "executing",
          detail: `${data.actions?.length || 0} actions planned — risk: ${data.risk_level}`,
          timestamp,
          data,
        })
        break

      case "execution_update":
        get().setArmStatus(data)
        if (data.status === "completed") {
          get().setPipelineStatus("completed")
          get().addReasoningStep({
            step: "completed",
            detail: "Execution completed",
            timestamp,
          })
        } else if (data.status === "failed") {
          get().setPipelineStatus("error")
        } else if (data.status === "executing") {
          get().setPipelineStatus("executing")
        }
        break

      case "error":
        get().setPipelineStatus("error")
        get().addReasoningStep({
          step: "error",
          detail: data.message,
          timestamp,
        })
        break

      case "homer_result":
        get().addHomerResult({ ...data, timestamp })
        break

      case "security_eval":
        get().setSecurityEval({ ...data, timestamp })
        break

      default:
        break
    }
  },

  // Reset for new command
  resetPipeline: () =>
    set({
      reasoningSteps: [],
      tavilyResults: [],
      homerResults: [],
      actionPlan: null,
      pendingApproval: null,
      pipelineStatus: "idle",
    }),
}))
