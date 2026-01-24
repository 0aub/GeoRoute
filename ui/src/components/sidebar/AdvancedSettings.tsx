import { Brain } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { useMission } from '@/hooks/useMission';

export const AdvancedSettings = () => {
  const { advancedAnalytics, setAdvancedAnalytics } = useMission();

  return (
    <div className="space-y-3 p-4 bg-secondary/30 rounded-lg border border-border">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-500" />
          <Label htmlFor="advanced-analytics" className="cursor-pointer">
            Advanced Tactical Analytics
          </Label>
        </div>
        <Switch
          id="advanced-analytics"
          checked={advancedAnalytics}
          onCheckedChange={setAdvancedAnalytics}
        />
      </div>

      {advancedAnalytics && (
        <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t border-border">
          <p className="font-medium text-foreground">Enabled features:</p>
          <ul className="list-disc list-inside space-y-1 pl-2">
            <li>Tactical approach suggestions (flanking, diversions)</li>
            <li>Cover position identification</li>
            <li>Enemy weakness analysis</li>
            <li>Equipment recommendations</li>
            <li>Alternative tactical strategies</li>
          </ul>
          <p className="text-yellow-600 dark:text-yellow-500 pt-2">
            ⚠️ Increases planning time by ~10-15 seconds
          </p>
        </div>
      )}
    </div>
  );
};
