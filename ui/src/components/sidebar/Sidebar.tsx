import { Wifi, WifiOff } from 'lucide-react';
import { ActionButtons } from './ActionButtons';
import { UnitPlacement } from './UnitPlacement';
import { TacticalRouteResults } from './TacticalRouteResults';
import { AdvancedSettings } from './AdvancedSettings';
import { TacticalReportModal } from '@/components/tactical/TacticalReportModal';
import { Separator } from '@/components/ui/separator';

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
  return (
    <aside className="w-52 h-full bg-background-panel border-r border-border flex flex-col shrink-0">
      {/* Logo Header - Compact */}
      <div className="p-2 border-b border-border flex flex-col items-center">
        <img
          src="/logo.svg"
          alt="GeoRoute"
          className="w-full max-w-[140px] h-auto mb-1"
          style={{ minHeight: '40px' }}
        />
        {/* Status Bar */}
        <div className="flex items-center justify-end w-full">
          <div className="flex items-center gap-1">
            <span className="text-[9px] text-foreground-muted">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
            {isConnected ? (
              <Wifi className="w-2.5 h-2.5 text-success" />
            ) : (
              <WifiOff className="w-2.5 h-2.5 text-danger" />
            )}
          </div>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto tactical-scroll p-2 space-y-2">
        {/* Unit Placement for Tactical Planning */}
        <UnitPlacement />

        <Separator className="bg-border" />

        {/* Advanced Analytics Settings */}
        <AdvancedSettings />

        <Separator className="bg-border" />

        <ActionButtons
          onPlanTacticalAttack={onPlanTacticalAttack}
          isLoading={isLoading}
        />

        {/* Tactical Route Results */}
        <TacticalRouteResults onRegenerate={onPlanTacticalAttack} />
      </div>

      {/* Tactical Report Modal */}
      <TacticalReportModal />
    </aside>
  );
};
