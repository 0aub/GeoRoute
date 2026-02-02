import { Users, Crosshair, Shield, Heart } from 'lucide-react';
import { useMission } from '@/hooks/useMission';
import { Slider } from '@/components/ui/slider';

interface UnitRowProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  max: number;
  onChange: (value: number) => void;
  color?: string;
}

function UnitRow({ icon, label, value, max, onChange, color = 'text-muted-foreground' }: UnitRowProps) {
  return (
    <div className="flex items-center gap-3">
      <div className={`${color}`}>{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-muted-foreground">{label}</span>
          <span className="text-xs font-mono">{value}</span>
        </div>
        <Slider
          value={[value]}
          onValueChange={([v]) => onChange(v)}
          max={max}
          min={0}
          step={1}
          className="w-full"
        />
      </div>
    </div>
  );
}

export function UnitCompositionPanel() {
  const { unitComposition, setUnitComposition, drawnWaypoints } = useMission();

  // Calculate remaining slots
  const assignedUnits =
    unitComposition.riflemen +
    unitComposition.snipers +
    unitComposition.support +
    unitComposition.medics;
  const availableSlots = unitComposition.squadSize - assignedUnits;

  // Don't show if no waypoints
  if (drawnWaypoints.length < 2) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Unit Composition
      </div>

      {/* Squad Size */}
      <div className="flex items-center justify-between p-2 rounded bg-background-deep">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">Squad Size</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="w-6 h-6 rounded bg-background hover:bg-muted flex items-center justify-center text-sm"
            onClick={() =>
              setUnitComposition({ squadSize: Math.max(2, unitComposition.squadSize - 1) })
            }
          >
            -
          </button>
          <span className="w-6 text-center font-mono">{unitComposition.squadSize}</span>
          <button
            className="w-6 h-6 rounded bg-background hover:bg-muted flex items-center justify-center text-sm"
            onClick={() =>
              setUnitComposition({ squadSize: Math.min(12, unitComposition.squadSize + 1) })
            }
          >
            +
          </button>
        </div>
      </div>

      {/* Available Slots Indicator */}
      {availableSlots < 0 && (
        <div className="text-xs text-danger">
          {Math.abs(availableSlots)} units over squad size limit
        </div>
      )}

      {/* Unit Types */}
      <div className="space-y-3">
        <UnitRow
          icon={<Users className="h-4 w-4" />}
          label="Riflemen"
          value={unitComposition.riflemen}
          max={unitComposition.squadSize}
          onChange={(v) => setUnitComposition({ riflemen: v })}
        />
        <UnitRow
          icon={<Crosshair className="h-4 w-4" />}
          label="Snipers"
          value={unitComposition.snipers}
          max={Math.min(3, unitComposition.squadSize)}
          onChange={(v) => setUnitComposition({ snipers: v })}
          color="text-yellow-500"
        />
        <UnitRow
          icon={<Shield className="h-4 w-4" />}
          label="Support/MG"
          value={unitComposition.support}
          max={Math.min(2, unitComposition.squadSize)}
          onChange={(v) => setUnitComposition({ support: v })}
          color="text-orange-500"
        />
        <UnitRow
          icon={<Heart className="h-4 w-4" />}
          label="Medics"
          value={unitComposition.medics}
          max={Math.min(2, unitComposition.squadSize)}
          onChange={(v) => setUnitComposition({ medics: v })}
          color="text-red-400"
        />
      </div>

      {/* Summary */}
      <div className="text-xs text-muted-foreground pt-2 border-t border-border">
        {assignedUnits} of {unitComposition.squadSize} positions assigned
        {availableSlots > 0 && (
          <span className="text-primary ml-1">({availableSlots} available)</span>
        )}
      </div>
    </div>
  );
}
