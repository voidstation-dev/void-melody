import { useTranslation } from "@/hooks/use-translation"
import { useVoxCpmStore, type VoxCpmTabId } from "@/stores/voxcpm-store"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CloneVoiceTab } from "./clone-voice-tab"
import { EmotionalTtsTab } from "./emotional-tts-tab"
import { ClonedVoicesTab } from "./cloned-voices-tab"
import { RuntimeTab } from "./runtime-tab"

const TAB_VALUES: VoxCpmTabId[] = ["clone", "emotional", "voices", "runtime"]

export function VoxCpmTabs() {
  const { t } = useTranslation()
  const activeTab = useVoxCpmStore((s) => s.activeTab)
  const setActiveTab = useVoxCpmStore((s) => s.setActiveTab)

  const tabLabels: Record<VoxCpmTabId, string> = {
    clone: t("voxcpm.tabClone"),
    emotional: t("voxcpm.tabEmotional"),
    voices: t("voxcpm.tabVoices"),
    runtime: t("voxcpm.tabRuntime"),
  }

  return (
    <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as VoxCpmTabId)}>
      <TabsList>
        {TAB_VALUES.map((tab) => (
          <TabsTrigger key={tab} value={tab}>
            {tabLabels[tab]}
          </TabsTrigger>
        ))}
      </TabsList>
      <TabsContent value="clone">
        <CloneVoiceTab />
      </TabsContent>
      <TabsContent value="emotional">
        <EmotionalTtsTab />
      </TabsContent>
      <TabsContent value="voices">
        <ClonedVoicesTab />
      </TabsContent>
      <TabsContent value="runtime">
        <RuntimeTab />
      </TabsContent>
    </Tabs>
  )
}