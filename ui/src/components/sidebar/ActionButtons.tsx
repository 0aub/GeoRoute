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
    <div className="space-y-3">
      {/* Plan Tactical Attack Button */}
      <Button
        className="w-full btn-tactical bg-primary hover:bg-primary/90 text-primary-foreground glow-border"
        onClick={onPlanTacticalAttack}
        disabled={!canPlanTactical}
      >
        {isLoading ? (
          <>
            <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin mr-2" />
            Generating Routes...
          </>
        ) : (
          <>
            <Crosshair className="w-4 h-4 mr-2" />
            Plan Tactical Attack
          </>
        )}
      </Button>

      <Button
        variant="ghost"
        className="w-full btn-tactical text-danger hover:text-danger hover:bg-danger/10"
        onClick={clearAll}
        disabled={isLoading}
      >
        <XCircle className="w-4 h-4 mr-2" />
        Clear All
      </Button>
    </div>
  );
};
