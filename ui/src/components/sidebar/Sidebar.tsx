import { Wifi, WifiOff, Database } from 'lucide-react';
import { NoGoZones } from './NoGoZones';
import { ActionButtons } from './ActionButtons';
import { UnitPlacement } from './UnitPlacement';
import { TacticalRouteResults } from './TacticalRouteResults';
import { AdvancedSettings } from './AdvancedSettings';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

interface SidebarProps {
  onPlanTacticalAttack: () => void;
  isLoading: boolean;
  isConnected?: boolean;
}

export const Sidebar = ({
  onPlanTacticalAttack,
  isLoading,
  isConnected = true,
}: SidebarProps) => {
  const navigate = useNavigate();

  return (
    <aside className="w-80 h-full bg-background-panel border-r border-border flex flex-col shrink-0">
      {/* Logo Header - Large and Centered */}
      <div className="p-6 border-b border-border flex flex-col items-center">
        <img
          src="/logo.svg"
          alt="GeoRoute"
          className="w-full max-w-[260px] h-auto mb-4"
          style={{ minHeight: '100px' }}
        />
        {/* Status Bar */}
        <div className="flex items-center justify-between w-full mt-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => navigate('/backlog')}
            className="gap-1 text-foreground-muted hover:text-foreground"
          >
            <Database className="w-4 h-4" />
            Backlog
          </Button>
          <div className="flex items-center gap-2">
            <span className="text-xs text-foreground-muted">
              {isConnected ? 'Connected' : 'Offline'}
            </span>
            {isConnected ? (
              <Wifi className="w-4 h-4 text-success" />
            ) : (
              <WifiOff className="w-4 h-4 text-danger" />
            )}
          </div>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto tactical-scroll p-4 space-y-6">
        {/* Unit Placement for Tactical Planning */}
        <UnitPlacement />

        <Separator className="bg-border" />

        {/* No-Go Zones */}
        <NoGoZones />

        <Separator className="bg-border" />

        {/* Advanced Analytics Settings */}
        <AdvancedSettings />

        <Separator className="bg-border" />

        <ActionButtons
          onPlanTacticalAttack={onPlanTacticalAttack}
          isLoading={isLoading}
        />

        {/* Tactical Route Results */}
        <TacticalRouteResults />
      </div>
    </aside>
  );
};
