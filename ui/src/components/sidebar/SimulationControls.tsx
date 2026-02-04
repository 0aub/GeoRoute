import { useState } from 'react';
import {
  Target,
  Users,
  Route,
  Pencil,
  Undo2,
  Trash2,
  Check,
  RotateCw,
  ChevronDown,
  Eye,
  Crosshair,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  useMission,
  type SimEnemyType,
  type SimFriendlyType,
  ENEMY_VISION_SPECS,
} from '@/hooks/useMission';
import { cn } from '@/lib/utils';

// Enemy type display info with professional styling and SVG icons
const ENEMY_TYPE_INFO: Record<SimEnemyType, { label: string; color: string; icon: JSX.Element }> = {
  sniper: {
    label: 'Sniper',
    color: '#dc2626',
    icon: (
      <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5">
        <circle cx="12" cy="12" r="4" />
        <line x1="12" y1="3" x2="12" y2="7" />
        <line x1="12" y1="17" x2="12" y2="21" />
        <line x1="3" y1="12" x2="7" y2="12" />
        <line x1="17" y1="12" x2="21" y2="12" />
      </svg>
    ),
  },
  rifleman: {
    label: 'Rifleman',
    color: '#dc2626',
    icon: (
      <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
        <line x1="6" y1="19" x2="12" y2="5" />
        <line x1="18" y1="19" x2="12" y2="5" />
      </svg>
    ),
  },
  observer: {
    label: 'Observer',
    color: '#dc2626',
    icon: (
      <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5">
        <circle cx="12" cy="12" r="7" />
        <circle cx="12" cy="12" r="2.5" fill="currentColor" />
      </svg>
    ),
  },
};

// Friendly type display info with professional styling and SVG icons
const FRIENDLY_TYPE_INFO: Record<SimFriendlyType, { label: string; color: string; icon: JSX.Element }> = {
  rifleman: {
    label: 'Rifleman',
    color: '#2563eb',
    icon: (
      <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
        <line x1="6" y1="19" x2="12" y2="5" />
        <line x1="18" y1="19" x2="12" y2="5" />
      </svg>
    ),
  },
  sniper: {
    label: 'Sniper',
    color: '#2563eb',
    icon: (
      <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5">
        <circle cx="12" cy="12" r="4" />
        <line x1="12" y1="3" x2="12" y2="7" />
        <line x1="12" y1="17" x2="12" y2="21" />
        <line x1="3" y1="12" x2="7" y2="12" />
        <line x1="17" y1="12" x2="21" y2="12" />
      </svg>
    ),
  },
  medic: {
    label: 'Medic',
    color: '#2563eb',
    icon: (
      <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5">
        <line x1="12" y1="4" x2="12" y2="20" />
        <line x1="4" y1="12" x2="20" y2="12" />
      </svg>
    ),
  },
};

export function SimulationControls() {
  const {
    mapMode,
    setMapMode,
    simEnemies,
    simFriendlies,
    drawnWaypoints,
    selectedSimEnemyType,
    selectedSimFriendlyType,
    setSelectedSimEnemyType,
    setSelectedSimFriendlyType,
    removeSimEnemy,
    removeSimFriendly,
    removeDrawnWaypoint,
    clearDrawnWaypoints,
    clearSimulation,
    updateSimEnemyFacing,
  } = useMission();

  const [enemiesOpen, setEnemiesOpen] = useState(true);
  const [friendliesOpen, setFriendliesOpen] = useState(true);
  const [routeOpen, setRouteOpen] = useState(true);

  const isPlacingEnemy = mapMode === 'place-sim-enemy';
  const isPlacingFriendly = mapMode === 'place-sim-friendly';
  const isDrawingRoute = mapMode === 'draw-route';

  const handleUndoLastWaypoint = () => {
    if (drawnWaypoints.length > 0) {
      removeDrawnWaypoint(drawnWaypoints.length - 1);
    }
  };

  return (
    <div className="space-y-2">
      {/* Enemy Units Section */}
      <Collapsible open={enemiesOpen} onOpenChange={setEnemiesOpen}>
        <CollapsibleTrigger className="flex items-center justify-between w-full p-1.5 rounded hover:bg-secondary/50 transition-colors">
          <div className="flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5 text-red-500" />
            <span className="text-xs font-medium">Enemy Units</span>
            <span className="text-[10px] text-muted-foreground">({simEnemies.length})</span>
          </div>
          <ChevronDown className={cn('w-3.5 h-3.5 transition-transform', enemiesOpen && 'rotate-180')} />
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-1.5 space-y-1.5">
          {/* Enemy Type Selector */}
          <div className="flex gap-1.5">
            <Select
              value={selectedSimEnemyType}
              onValueChange={(v) => setSelectedSimEnemyType(v as SimEnemyType)}
            >
              <SelectTrigger className="h-7 text-xs flex-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(ENEMY_TYPE_INFO) as SimEnemyType[]).map((type) => (
                  <SelectItem key={type} value={type} className="text-xs">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-6 h-6 rounded-full flex items-center justify-center text-white shrink-0"
                        style={{ background: ENEMY_TYPE_INFO[type].color }}
                      >
                        {ENEMY_TYPE_INFO[type].icon}
                      </span>
                      <span className="font-medium">{ENEMY_TYPE_INFO[type].label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant={isPlacingEnemy ? 'default' : 'outline'}
              size="sm"
              className="h-7 px-2"
              onClick={() => setMapMode(isPlacingEnemy ? 'idle' : 'place-sim-enemy')}
            >
              {isPlacingEnemy ? <Check className="w-3.5 h-3.5" /> : <Target className="w-3.5 h-3.5" />}
            </Button>
          </div>

          {/* Enemy List with Rotation Controls */}
          {simEnemies.length > 0 && (
            <div className="space-y-1.5 max-h-32 overflow-y-auto">
              {simEnemies.map((enemy, idx) => (
                <div
                  key={enemy.id}
                  className="p-2 rounded border"
                  style={{
                    background: `${ENEMY_TYPE_INFO[enemy.type].color}15`,
                    borderColor: `${ENEMY_TYPE_INFO[enemy.type].color}40`,
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-7 h-7 rounded-full flex items-center justify-center text-white shrink-0"
                        style={{ background: ENEMY_TYPE_INFO[enemy.type].color }}
                      >
                        {ENEMY_TYPE_INFO[enemy.type].icon}
                      </span>
                      <div className="flex flex-col">
                        <span className="text-[11px] font-medium">{ENEMY_TYPE_INFO[enemy.type].label} #{idx + 1}</span>
                        <span className="text-[9px] text-muted-foreground">
                          {ENEMY_VISION_SPECS[enemy.type].distance}m • {ENEMY_VISION_SPECS[enemy.type].angle}°
                        </span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 hover:text-red-500"
                      onClick={() => removeSimEnemy(enemy.id)}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                  {/* Rotation Slider */}
                  <div className="flex items-center gap-2 mt-2">
                    <RotateCw className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                    <input
                      type="range"
                      min="0"
                      max="359"
                      value={enemy.facing}
                      onChange={(e) => updateSimEnemyFacing(enemy.id, parseInt(e.target.value))}
                      className="flex-1 h-1.5 accent-current rounded"
                      style={{ accentColor: ENEMY_TYPE_INFO[enemy.type].color }}
                    />
                    <span className="text-[10px] font-mono text-muted-foreground w-8 text-right">{enemy.facing}°</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {simEnemies.length === 0 && (
            <p className="text-[10px] text-muted-foreground text-center py-2">
              Click map to place enemies
            </p>
          )}
        </CollapsibleContent>
      </Collapsible>

      {/* Friendly Units Section */}
      <Collapsible open={friendliesOpen} onOpenChange={setFriendliesOpen}>
        <CollapsibleTrigger className="flex items-center justify-between w-full p-1.5 rounded hover:bg-secondary/50 transition-colors">
          <div className="flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-xs font-medium">Friendly Units</span>
            <span className="text-[10px] text-muted-foreground">({simFriendlies.length})</span>
          </div>
          <ChevronDown className={cn('w-3.5 h-3.5 transition-transform', friendliesOpen && 'rotate-180')} />
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-1.5 space-y-1.5">
          {/* Friendly Type Selector */}
          <div className="flex gap-1.5">
            <Select
              value={selectedSimFriendlyType}
              onValueChange={(v) => setSelectedSimFriendlyType(v as SimFriendlyType)}
            >
              <SelectTrigger className="h-7 text-xs flex-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(FRIENDLY_TYPE_INFO) as SimFriendlyType[]).map((type) => (
                  <SelectItem key={type} value={type} className="text-xs">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-6 h-6 rounded flex items-center justify-center text-white shrink-0"
                        style={{ background: FRIENDLY_TYPE_INFO[type].color }}
                      >
                        {FRIENDLY_TYPE_INFO[type].icon}
                      </span>
                      <span className="font-medium">{FRIENDLY_TYPE_INFO[type].label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant={isPlacingFriendly ? 'default' : 'outline'}
              size="sm"
              className="h-7 px-2"
              onClick={() => setMapMode(isPlacingFriendly ? 'idle' : 'place-sim-friendly')}
            >
              {isPlacingFriendly ? <Check className="w-3.5 h-3.5" /> : <Users className="w-3.5 h-3.5" />}
            </Button>
          </div>

          {/* Friendly List */}
          {simFriendlies.length > 0 && (
            <div className="space-y-1.5 max-h-28 overflow-y-auto">
              {simFriendlies.map((friendly, idx) => (
                <div
                  key={friendly.id}
                  className="flex items-center justify-between p-2 rounded bg-blue-500/10 border border-blue-500/30"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-7 h-7 rounded flex items-center justify-center text-white bg-blue-600 shrink-0"
                    >
                      {FRIENDLY_TYPE_INFO[friendly.type].icon}
                    </span>
                    <span className="text-[11px] font-medium">{FRIENDLY_TYPE_INFO[friendly.type].label} #{idx + 1}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 hover:text-red-500"
                    onClick={() => removeSimFriendly(friendly.id)}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {simFriendlies.length === 0 && (
            <p className="text-[10px] text-muted-foreground text-center py-2">
              Click map to place friendlies
            </p>
          )}
        </CollapsibleContent>
      </Collapsible>

      {/* Route Drawing Section */}
      <Collapsible open={routeOpen} onOpenChange={setRouteOpen}>
        <CollapsibleTrigger className="flex items-center justify-between w-full p-1.5 rounded hover:bg-secondary/50 transition-colors">
          <div className="flex items-center gap-1.5">
            <Route className="w-3.5 h-3.5 text-green-500" />
            <span className="text-xs font-medium">Movement Route</span>
            <span className="text-[10px] text-muted-foreground">({drawnWaypoints.length} pts)</span>
          </div>
          <ChevronDown className={cn('w-3.5 h-3.5 transition-transform', routeOpen && 'rotate-180')} />
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-1.5 space-y-1.5">
          {/* Drawing Controls */}
          <Button
            variant={isDrawingRoute ? 'secondary' : 'outline'}
            size="sm"
            className="w-full h-7 text-xs gap-1.5"
            onClick={() => setMapMode(isDrawingRoute ? 'idle' : 'draw-route')}
          >
            {isDrawingRoute ? (
              <>
                <Check className="w-3 h-3" />
                Done Drawing
              </>
            ) : (
              <>
                <Pencil className="w-3 h-3" />
                {drawnWaypoints.length > 0 ? 'Continue Drawing' : 'Draw Route'}
              </>
            )}
          </Button>

          {drawnWaypoints.length > 0 && (
            <div className="flex gap-1.5">
              <Button
                variant="ghost"
                size="sm"
                className="flex-1 h-6 text-[10px] gap-1"
                onClick={handleUndoLastWaypoint}
              >
                <Undo2 className="w-3 h-3" />
                Undo
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="flex-1 h-6 text-[10px] gap-1 text-orange-500 hover:text-orange-500"
                onClick={clearDrawnWaypoints}
              >
                <Trash2 className="w-3 h-3" />
                Clear Route
              </Button>
            </div>
          )}

          {drawnWaypoints.length === 0 && (
            <p className="text-[10px] text-muted-foreground text-center py-2">
              Click map to draw movement route
            </p>
          )}
        </CollapsibleContent>
      </Collapsible>

      {/* Clear All Button */}
      {(simEnemies.length > 0 || simFriendlies.length > 0 || drawnWaypoints.length > 0) && (
        <Button
          variant="ghost"
          size="sm"
          className="w-full h-6 text-[10px] text-muted-foreground hover:text-red-500"
          onClick={clearSimulation}
        >
          <Trash2 className="w-3 h-3 mr-1" />
          Clear All
        </Button>
      )}
    </div>
  );
}
