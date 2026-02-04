import { FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useMission } from '@/hooks/useMission';

export function SimulationResults() {
  const { simulationResult, setReportModalOpen } = useMission();

  if (!simulationResult) {
    return null;
  }

  return (
    <div className="space-y-2 pt-2">
      <Button
        variant="outline"
        className="w-full h-auto py-3 flex items-center justify-center gap-2"
        onClick={() => setReportModalOpen(true)}
      >
        <FileText className="w-4 h-4 text-purple-500" />
        <span className="text-sm">View Analysis Report</span>
      </Button>
    </div>
  );
}
