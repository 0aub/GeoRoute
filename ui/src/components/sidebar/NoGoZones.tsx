import { Shield, Trash2, Pentagon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { useMission } from '@/hooks/useMission';

export const NoGoZones = () => {
  const { noGoZones, removeNoGoZone, mapMode, setMapMode } = useMission();

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground uppercase tracking-wider">
        <Shield className="w-4 h-4 text-danger" />
        <span>No-Go Zones</span>
      </div>

      <Button
        variant={mapMode === 'draw-no-go' ? 'destructive' : 'outline'}
        className="w-full btn-tactical"
        onClick={() => setMapMode(mapMode === 'draw-no-go' ? 'idle' : 'draw-no-go')}
      >
        <Pentagon className="w-4 h-4 mr-2" />
        {mapMode === 'draw-no-go' ? 'Cancel Drawing' : 'Draw No-Go Zone'}
      </Button>

      {mapMode === 'draw-no-go' && (
        <p className="text-xs text-warning bg-warning/10 p-2 rounded border border-warning/30">
          Click on the map to draw polygon vertices. Double-click to finish.
        </p>
      )}

      {noGoZones.length > 0 ? (
        <div className="space-y-1">
          {noGoZones.map((zone, index) => (
            <div
              key={zone.id}
              className="flex items-center gap-2 p-2 bg-danger/10 border border-danger/30 rounded text-xs"
            >
              <Pentagon className="w-4 h-4 text-danger" />
              <span className="flex-1 truncate font-medium">
                {zone.name || `Zone ${index + 1}`}
              </span>
              <span className="text-foreground-muted">
                {zone.coordinates.length} pts
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-danger hover:text-danger hover:bg-danger/10"
                onClick={() => removeNoGoZone(zone.id)}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-foreground-muted italic">
          No restricted zones defined.
        </p>
      )}
    </div>
  );
};
