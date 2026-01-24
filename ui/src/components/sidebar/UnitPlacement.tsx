import { useMission } from '@/hooks/useMission';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Trash2, Users, Crosshair } from 'lucide-react';

export const UnitPlacement = () => {
  const {
    soldiers,
    enemies,
    mapMode,
    setMapMode,
    removeSoldier,
    removeEnemy,
  } = useMission();

  const handlePlaceSoldier = () => {
    setMapMode('place-soldier');
  };

  const handlePlaceEnemy = () => {
    setMapMode('place-enemy');
  };

  return (
    <div className="space-y-6">
      {/* Friendly Units Section */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="flex items-center gap-2">
            <Users className="w-4 h-4 text-blue-500" />
            Friendly Units ({soldiers.length})
          </Label>
        </div>

        <Button
          onClick={handlePlaceSoldier}
          className="w-full bg-blue-500 hover:bg-blue-600"
          variant={mapMode === 'place-soldier' ? 'default' : 'outline'}
        >
          {mapMode === 'place-soldier' ? 'Click map to place' : 'Place Friendly Unit'}
        </Button>

        {/* Placed soldiers list */}
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {soldiers.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">
              No friendly units placed yet
            </p>
          )}
          {soldiers.map((soldier, index) => (
            <div
              key={soldier.unit_id}
              className="flex items-center justify-between bg-secondary p-2 rounded text-sm"
            >
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
                Friendly Unit #{index + 1}
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => removeSoldier(soldier.unit_id)}
                className="h-6 w-6 p-0"
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      {/* Enemy Units Section */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="flex items-center gap-2">
            <Crosshair className="w-4 h-4 text-red-500" />
            Enemy Units ({enemies.length})
          </Label>
        </div>

        <Button
          onClick={handlePlaceEnemy}
          className="w-full bg-red-500 hover:bg-red-600"
          variant={mapMode === 'place-enemy' ? 'default' : 'outline'}
        >
          {mapMode === 'place-enemy' ? 'Click map to place' : 'Place Enemy Unit'}
        </Button>

        {/* Placed enemies list */}
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {enemies.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">
              No enemy units placed yet
            </p>
          )}
          {enemies.map((enemy, index) => (
            <div
              key={enemy.unit_id}
              className="flex items-center justify-between bg-secondary p-2 rounded text-sm"
            >
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 bg-red-500 rounded-full" />
                Enemy Unit #{index + 1}
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => removeEnemy(enemy.unit_id)}
                className="h-6 w-6 p-0"
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      {/* Instructions */}
      <div className="text-xs text-muted-foreground bg-secondary/50 p-3 rounded">
        <strong>Instructions:</strong>
        <ul className="list-disc list-inside mt-1 space-y-1">
          <li>Click "Place Friendly Unit" or "Place Enemy Unit"</li>
          <li>Click on the map to place the unit</li>
          <li>Drag units to reposition them</li>
          <li>Click trash icon to remove units</li>
        </ul>
      </div>
    </div>
  );
};
