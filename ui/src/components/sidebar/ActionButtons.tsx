import { XCircle, Crosshair, Search, Radar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useMission } from '@/hooks/useMission';

interface ActionButtonsProps {
  onPlanTacticalAttack: () => void;
  onEvaluateRoute?: () => void;
  isLoading: boolean;
}

export const ActionButtons = ({
  onPlanTacticalAttack,
  onEvaluateRoute,
  isLoading,
}: ActionButtonsProps) => {
  const {
    soldiers,
    enemies,
    clearAll,
    routeMode,
    drawnWaypoints,
    isEvaluating,
    simEnemies,
    simFriendlies,
  } = useMission();

  const canPlanTactical = soldiers.length > 0 && enemies.length > 0 && !isLoading;

  // For simulation mode: need route + at least one enemy
  const canEvaluateSimulation =
    drawnWaypoints.length >= 2 &&
    simEnemies.length > 0 &&
    !isLoading &&
    !isEvaluating;

  // Manual draw mode shows Analyze Tactical button
  if (routeMode === 'manual-draw') {
    return (
      <div className="space-y-1.5">
        <Button
          className="w-full h-8 text-xs bg-primary hover:bg-primary/90 text-primary-foreground"
          onClick={onEvaluateRoute}
          disabled={!canEvaluateSimulation}
        >
          {isEvaluating ? (
            <>
              <div className="w-3 h-3 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin mr-1.5" />
              Analyzing...
            </>
          ) : (
            <>
              <Radar className="w-3.5 h-3.5 mr-1.5" />
              Analyze Tactical Plan
            </>
          )}
        </Button>

        {!canEvaluateSimulation && !isEvaluating && (
          <p className="text-[9px] text-muted-foreground text-center">
            {drawnWaypoints.length < 2 && 'Draw a route • '}
            {simEnemies.length === 0 && 'Add enemies'}
          </p>
        )}
      </div>
    );
  }

  // AI generate mode shows Plan Attack button
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
