import { Brain, FileText } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { useMission } from '@/hooks/useMission';

export const AdvancedSettings = () => {
  const {
    advancedAnalytics,
    setAdvancedAnalytics,
    tacticalAnalysisReport,
    tacticalReportHistory,
    setReportModalOpen,
  } = useMission();

  const hasReport = tacticalAnalysisReport !== null;
  const historyCount = tacticalReportHistory.length;

  return (
    <div className="space-y-1.5 p-1.5 bg-secondary/30 rounded border border-border">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Brain className="w-3 h-3 text-purple-500" />
          <Label htmlFor="advanced-analytics" className="cursor-pointer text-[10px]">
            Advanced Analytics
          </Label>
        </div>
        <Switch
          id="advanced-analytics"
          checked={advancedAnalytics}
          onCheckedChange={setAdvancedAnalytics}
          className="scale-75"
        />
      </div>

      {advancedAnalytics && !hasReport && (
        <p className="text-[9px] text-yellow-600">
          Generate routes for analysis
        </p>
      )}

      {(hasReport || historyCount > 0) && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => setReportModalOpen(true)}
          className="w-full h-6 text-[10px] gap-1"
        >
          <FileText className="w-3 h-3" />
          Report
          {historyCount > 0 && (
            <span className="ml-auto text-[9px] text-muted-foreground">
              ({historyCount})
            </span>
          )}
        </Button>
      )}
    </div>
  );
};
