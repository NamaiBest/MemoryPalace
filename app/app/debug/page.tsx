import { DebugPage } from "@/components/debug/DebugPage";

export const metadata = {
  title: "Diagnostics · MemoryPalace",
  description: "Live state of the EEG, backend, phone and captured media.",
};

export default function Page() {
  return <DebugPage />;
}
