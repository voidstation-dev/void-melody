import { useMutation, useQueryClient } from "@tanstack/react-query"
import { analyzeVoiceSample, cloneVoiceProfile } from "@/lib/voice-lab-api"

export function useVoiceLab() {
  const queryClient = useQueryClient()
  const analysis = useMutation({ mutationFn: analyzeVoiceSample })
  const clone = useMutation({
    mutationFn: cloneVoiceProfile,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["custom-voices"] }),
  })
  return { analysis, clone }
}
