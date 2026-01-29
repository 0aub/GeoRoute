import { useMission, getUnitDisplayName } from '@/hooks/useMission';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Trash2, Users, Crosshair } from 'lucide-react';

// Helper to get short display name for sidebar
const getShortName = (unit: { plan_id?: number; plan_unit_number?: number; is_friendly: boolean }, index: number): string => {
  if (unit.plan_id !== undefined && unit.plan_unit_number !== undefined) {
    return `P${unit.plan_id} #${unit.plan_unit_number}`;
  }
  return `New #${index + 1}`;
};

export const UnitPlacement = () => {
  const {
    soldiers,
    enemies,
    mapMode,
    setMapMode,
    removeSoldier,
    removeEnemy,
  } = useMission();

  // Group units by plan
  const assignedSoldiers = soldiers.filter(s => s.plan_id !== undefined);
  const unassignedSoldiers = soldiers.filter(s => s.plan_id === undefined);
  const assignedEnemies = enemies.filter(e => e.plan_id !== undefined);
  const unassignedEnemies = enemies.filter(e => e.plan_id === undefined);

  return (
    <div className="space-y-2">
      {/* Friendly Units */}
      <div className="space-y-1">
        <Label className="flex items-center gap-1 text-[10px]">
          <Users className="w-2.5 h-2.5 text-blue-500" />
          Friendly ({soldiers.length})
        </Label>
        <Button
          onClick={() => setMapMode('place-soldier')}
          className="w-full bg-blue-500 hover:bg-blue-600 h-6 text-[10px]"
          variant={mapMode === 'place-soldier' ? 'default' : 'outline'}
        >
          {mapMode === 'place-soldier' ? 'Click map to place' : 'Place Friendly'}
        </Button>
        {soldiers.length > 0 && (
          <div className="space-y-0.5 max-h-16 overflow-y-auto">
            {soldiers.map((soldier, i) => (
              <div
                key={soldier.unit_id}
                className="flex items-center justify-between bg-secondary/50 px-1.5 py-0.5 rounded text-[9px]"
              >
                <span className="flex items-center gap-1">
                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                  {getShortName(soldier, unassignedSoldiers.indexOf(soldier))}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => removeSoldier(soldier.unit_id)}
                  className="h-4 w-4 p-0"
                >
                  <Trash2 className="w-2 h-2" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Enemy Units */}
      <div className="space-y-1">
        <Label className="flex items-center gap-1 text-[10px]">
          <Crosshair className="w-2.5 h-2.5 text-red-500" />
          Enemy ({enemies.length})
        </Label>
        <Button
          onClick={() => setMapMode('place-enemy')}
          className="w-full bg-red-500 hover:bg-red-600 h-6 text-[10px]"
          variant={mapMode === 'place-enemy' ? 'default' : 'outline'}
        >
          {mapMode === 'place-enemy' ? 'Click map to place' : 'Place Enemy'}
        </Button>
        {enemies.length > 0 && (
          <div className="space-y-0.5 max-h-16 overflow-y-auto">
            {enemies.map((enemy, i) => (
              <div
                key={enemy.unit_id}
                className="flex items-center justify-between bg-secondary/50 px-1.5 py-0.5 rounded text-[9px]"
              >
                <span className="flex items-center gap-1">
                  <div className="w-1.5 h-1.5 bg-red-500 rounded-full" />
                  {getShortName(enemy, unassignedEnemies.indexOf(enemy))}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => removeEnemy(enemy.unit_id)}
                  className="h-4 w-4 p-0"
                >
                  <Trash2 className="w-2 h-2" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
