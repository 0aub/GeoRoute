import { Route, Pencil, Undo2, Trash2, Cpu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useMission, type RouteMode } from '@/hooks/useMission';

export function RouteDrawingControls() {
  const {
    routeMode,
    setRouteMode,
    drawnWaypoints,
    removeDrawnWaypoint,
    clearDrawnWaypoints,
    mapMode,
    setMapMode,
  } = useMission();

  const handleModeChange = (mode: RouteMode) => {
    setRouteMode(mode);
    if (mode === 'manual-draw') {
      setMapMode('draw-route');
    } else {
      setMapMode('idle');
    }
  };

  const handleUndoLast = () => {
    if (drawnWaypoints.length > 0) {
      removeDrawnWaypoint(drawnWaypoints.length - 1);
    }
  };

  return (
    <div className="space-y-3">
      <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Route Mode
      </div>

      {/* Mode Toggle */}
      <div className="flex gap-2">
        <Button
          variant={routeMode === 'ai-generate' ? 'default' : 'outline'}
          size="sm"
          className="flex-1 gap-1.5"
          onClick={() => handleModeChange('ai-generate')}
        >
          <Cpu className="h-3.5 w-3.5" />
          AI Generate
        </Button>
        <Button
          variant={routeMode === 'manual-draw' ? 'default' : 'outline'}
          size="sm"
          className="flex-1 gap-1.5"
          onClick={() => handleModeChange('manual-draw')}
        >
          <Pencil className="h-3.5 w-3.5" />
          Draw Route
        </Button>
      </div>

      {/* Manual Draw Controls */}
      {routeMode === 'manual-draw' && (
        <div className="space-y-2 pt-2 border-t border-border">
          {/* Instructions */}
          <div className="text-xs text-muted-foreground">
            {mapMode === 'draw-route' ? (
              <span className="text-primary">Click on the map to add waypoints</span>
            ) : (
              <span>Click "Start Drawing" to begin</span>
            )}
          </div>

          {/* Waypoint Count */}
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1.5">
              <Route className="h-3.5 w-3.5 text-primary" />
              Waypoints
            </span>
            <span className="font-mono text-muted-foreground">
              {drawnWaypoints.length}
            </span>
          </div>

          {/* Drawing Controls */}
          <div className="flex gap-2">
            {mapMode !== 'draw-route' ? (
              <Button
                variant="outline"
                size="sm"
                className="flex-1 gap-1.5"
                onClick={() => setMapMode('draw-route')}
              >
                <Pencil className="h-3.5 w-3.5" />
                Start Drawing
              </Button>
            ) : (
              <Button
                variant="secondary"
                size="sm"
                className="flex-1 gap-1.5"
                onClick={() => setMapMode('idle')}
              >
                Done Drawing
              </Button>
            )}
          </div>

          {drawnWaypoints.length > 0 && (
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="flex-1 gap-1.5"
                onClick={handleUndoLast}
              >
                <Undo2 className="h-3.5 w-3.5" />
                Undo
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="flex-1 gap-1.5 text-danger hover:text-danger"
                onClick={clearDrawnWaypoints}
              >
                <Trash2 className="h-3.5 w-3.5" />
                Clear
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
