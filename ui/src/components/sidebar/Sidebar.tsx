import { useState } from 'react';
import { Wifi, WifiOff, ChevronLeft, ChevronRight, Route, Crosshair } from 'lucide-react';
import { ActionButtons } from './ActionButtons';
import { UnitPlacement } from './UnitPlacement';
import { TacticalRouteResults } from './TacticalRouteResults';
import { AdvancedSettings } from './AdvancedSettings';
import { SimulationControls } from './SimulationControls';
import { SimulationResults } from './SimulationResults';
import { TacticalReportModal } from '@/components/tactical/TacticalReportModal';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { useMission, type RouteMode } from '@/hooks/useMission';
import { cn } from '@/lib/utils';

interface SidebarProps {
  onPlanTacticalAttack: () => void;
  onEvaluateRoute: () => void;
  isLoading: boolean;
  isConnected?: boolean;
}

export const Sidebar = ({
  onPlanTacticalAttack,
  onEvaluateRoute,
  isLoading,
  isConnected = true,
}: SidebarProps) => {
  const { routeMode, setRouteMode, routeEvaluation, setMapMode } = useMission();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleModeChange = (mode: RouteMode) => {
    setRouteMode(mode);
    if (mode === 'manual-draw') {
      setMapMode('draw-route');
    } else {
      setMapMode('idle');
    }
  };

  // Collapsed sidebar - just icons
  if (isCollapsed) {
    return (
      <aside className="w-12 h-full bg-background-panel border-r border-border flex flex-col shrink-0">
        {/* Expand Button */}
        <div className="p-2 border-b border-border">
          <Button
            variant="ghost"
            size="sm"
            className="w-full h-8 p-0"
            onClick={() => setIsCollapsed(false)}
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>

        {/* Mode Icons */}
        <div className="flex-1 p-1 space-y-1">
          <Button
            variant={routeMode === 'ai-generate' ? 'default' : 'ghost'}
            size="sm"
            className="w-full h-8 p-0"
            onClick={() => handleModeChange('ai-generate')}
            title="Route Planning"
          >
            <Route className="w-4 h-4" />
          </Button>
          <Button
            variant={routeMode === 'manual-draw' ? 'default' : 'ghost'}
            size="sm"
            className="w-full h-8 p-0"
            onClick={() => handleModeChange('manual-draw')}
            title="Tactical Simulation"
          >
            <Crosshair className="w-4 h-4" />
          </Button>
        </div>

        {/* Status */}
        <div className="p-2 border-t border-border flex justify-center">
          {isConnected ? (
            <Wifi className="w-4 h-4 text-success" />
          ) : (
            <WifiOff className="w-4 h-4 text-danger" />
          )}
        </div>

        <TacticalReportModal />
      </aside>
    );
  }

  // Expanded sidebar
  return (
    <aside className="w-56 h-full bg-background-panel border-r border-border flex flex-col shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-border relative">
        {/* Collapse button - absolute positioned */}
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 h-6 w-6 p-0"
          onClick={() => setIsCollapsed(true)}
        >
          <ChevronLeft className="w-4 h-4" />
        </Button>

        {/* Logo - centered */}
        <div className="mb-2 flex justify-center">
          <img
            src="/logo.svg"
            alt="GeoRoute"
            className="h-32 w-auto"
          />
        </div>

        {/* Status */}
        <div className="flex items-center justify-end gap-1.5">
          <span className="text-[10px] text-foreground-muted">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
          {isConnected ? (
            <Wifi className="w-3 h-3 text-success" />
          ) : (
            <WifiOff className="w-3 h-3 text-danger" />
          )}
        </div>
      </div>

      {/* Mode Tabs */}
      <div className="p-2 border-b border-border">
        <div className="flex bg-secondary/50 rounded-md p-0.5">
          <button
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded text-xs font-medium transition-colors',
              routeMode === 'ai-generate'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
            onClick={() => handleModeChange('ai-generate')}
          >
            <Route className="w-4 h-4" />
            Route
          </button>
          <button
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded text-xs font-medium transition-colors',
              routeMode === 'manual-draw'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
            onClick={() => handleModeChange('manual-draw')}
          >
            <Crosshair className="w-4 h-4" />
            Tactic
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto tactical-scroll p-2 space-y-2">
        {/* AI Generate Mode */}
        {routeMode === 'ai-generate' && (
          <>
            <UnitPlacement />
            <Separator className="bg-border" />
            <AdvancedSettings />
            <Separator className="bg-border" />
            <ActionButtons
              onPlanTacticalAttack={onPlanTacticalAttack}
              isLoading={isLoading}
            />
            <TacticalRouteResults onRegenerate={onPlanTacticalAttack} />
          </>
        )}

        {/* Manual Draw Mode - Tactical Simulation */}
        {routeMode === 'manual-draw' && (
          <>
            <SimulationControls />
            <Separator className="bg-border" />
            <ActionButtons
              onPlanTacticalAttack={onPlanTacticalAttack}
              onEvaluateRoute={onEvaluateRoute}
              isLoading={isLoading}
            />
            <SimulationResults />
          </>
        )}
      </div>

      {/* Tactical Report Modal */}
      <TacticalReportModal />
    </aside>
  );
};
