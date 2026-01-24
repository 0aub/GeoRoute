import { Truck, ChevronDown } from 'lucide-react';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useMission } from '@/hooks/useMission';
import type { VehicleProfile } from '@/types';

// Default vehicles until API loads
const defaultVehicles: VehicleProfile[] = [
  { id: 'mrap', name: 'M-ATV MRAP', maxSlope: 35, weight: 14.5, weightUnit: 'tons' },
  { id: 'humvee', name: 'HMMWV Humvee', maxSlope: 40, weight: 3.5, weightUnit: 'tons' },
  { id: 'ltt', name: 'Light Tactical Truck', maxSlope: 30, weight: 5, weightUnit: 'tons' },
  { id: 'het', name: 'Heavy Equipment Transporter', maxSlope: 20, weight: 35, weightUnit: 'tons' },
];

interface VehicleSelectionProps {
  vehicles?: VehicleProfile[];
}

export const VehicleSelection = ({ vehicles = defaultVehicles }: VehicleSelectionProps) => {
  const { selectedVehicle, setSelectedVehicle } = useMission();

  const handleSelect = (vehicleId: string) => {
    const vehicle = vehicles.find((v) => v.id === vehicleId);
    setSelectedVehicle(vehicle || null);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground uppercase tracking-wider">
        <Truck className="w-4 h-4 text-primary" />
        <span>Vehicle Selection</span>
      </div>

      <Select value={selectedVehicle?.id || ''} onValueChange={handleSelect}>
        <SelectTrigger className="w-full bg-input border-border">
          <SelectValue placeholder="Select vehicle type" />
        </SelectTrigger>
        <SelectContent className="bg-background-panel border-border">
          {vehicles.map((vehicle) => (
            <SelectItem key={vehicle.id} value={vehicle.id}>
              {vehicle.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {selectedVehicle && (
        <div className="p-3 bg-muted/30 rounded-md border border-border/50 space-y-2">
          <h4 className="text-sm font-medium text-foreground">{selectedVehicle.name}</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="space-y-1">
              <span className="text-foreground-muted">Max Slope</span>
              <div className="font-mono text-foreground-accent font-semibold">
                {selectedVehicle.maxSlope}°
              </div>
            </div>
            <div className="space-y-1">
              <span className="text-foreground-muted">Weight</span>
              <div className="font-mono text-foreground font-semibold">
                {selectedVehicle.weight} {selectedVehicle.weightUnit}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
