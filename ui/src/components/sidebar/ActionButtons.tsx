import { XCircle, Crosshair } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useMission } from '@/hooks/useMission';

interface ActionButtonsProps {
  onPlanTacticalAttack: () => void;
  isLoading: boolean;
}

export const ActionButtons = ({
  onPlanTacticalAttack,
  isLoading,
}: ActionButtonsProps) => {
  const { soldiers, enemies, clearAll } = useMission();

  const canPlanTactical = soldiers.length > 0 && enemies.length > 0 && !isLoading;

  return (
    <div className="space-y-1.5">
      <Button
        className="w-full h-7 text-xs bg-primary hover:bg-primary/90 text-primary-foreground"
        onClick={onPlanTacticalAttack}
        disabled={!canPlanTactical}
      >
        {isLoading ? (
          <>
            <div className="w-3 h-3 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin mr-1.5" />
            Planning...
          </>
        ) : (
          <>
            <Crosshair className="w-3 h-3 mr-1.5" />
            Plan Attack
          </>
        )}
      </Button>

      <Button
        variant="ghost"
        className="w-full h-6 text-[10px] text-muted-foreground hover:text-danger hover:bg-danger/10"
        onClick={clearAll}
        disabled={isLoading}
      >
        <XCircle className="w-3 h-3 mr-1" />
        Clear All
      </Button>
    </div>
  );
};
