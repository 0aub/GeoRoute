import { Route, Pencil, Undo2, Trash2, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useMission } from '@/hooks/useMission';

export function RouteDrawingControls() {
  const {
    drawnWaypoints,
    removeDrawnWaypoint,
    clearDrawnWaypoints,
    mapMode,
    setMapMode,
  } = useMission();

  const handleUndoLast = () => {
    if (drawnWaypoints.length > 0) {
      removeDrawnWaypoint(drawnWaypoints.length - 1);
    }
  };

  const isDrawing = mapMode === 'draw-route';

  return (
    <div className="space-y-2">
      {/* Header with waypoint count */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
          Route Drawing
        </span>
        <span className="flex items-center gap-1 text-xs">
          <Route className="w-3 h-3 text-primary" />
          <span className="font-mono">{drawnWaypoints.length}</span>
        </span>
      </div>

      {/* Status / Instructions */}
      <div className="text-[10px] text-muted-foreground">
        {isDrawing ? (
          <span className="text-primary">Click map to add waypoints</span>
        ) : drawnWaypoints.length === 0 ? (
          <span>Start drawing to create a route</span>
        ) : (
          <span>{drawnWaypoints.length} waypoints placed</span>
        )}
      </div>

      {/* Main Action Button */}
      <Button
        variant={isDrawing ? 'secondary' : 'outline'}
        size="sm"
        className="w-full h-7 text-xs gap-1.5"
        onClick={() => setMapMode(isDrawing ? 'idle' : 'draw-route')}
      >
        {isDrawing ? (
          <>
            <Check className="w-3 h-3" />
            Done Drawing
          </>
        ) : (
          <>
            <Pencil className="w-3 h-3" />
            {drawnWaypoints.length > 0 ? 'Continue Drawing' : 'Start Drawing'}
          </>
        )}
      </Button>

      {/* Undo / Clear Controls */}
      {drawnWaypoints.length > 0 && (
        <div className="flex gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            className="flex-1 h-6 text-[10px] gap-1"
            onClick={handleUndoLast}
          >
            <Undo2 className="w-3 h-3" />
            Undo
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="flex-1 h-6 text-[10px] gap-1 text-danger hover:text-danger"
            onClick={clearDrawnWaypoints}
          >
            <Trash2 className="w-3 h-3" />
            Clear
          </Button>
        </div>
      )}
    </div>
  );
}
