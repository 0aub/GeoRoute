import { useState } from 'react';
import { MapPin, Plus, Trash2, Navigation } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useMission } from '@/hooks/useMission';

export const MissionInput = () => {
  const {
    startPoint,
    endPoint,
    waypoints,
    setStartPoint,
    setEndPoint,
    removeWaypoint,
    setMapMode,
    mapMode,
  } = useMission();

  const [startLat, setStartLat] = useState(startPoint?.lat.toString() || '');
  const [startLon, setStartLon] = useState(startPoint?.lon.toString() || '');
  const [endLat, setEndLat] = useState(endPoint?.lat.toString() || '');
  const [endLon, setEndLon] = useState(endPoint?.lon.toString() || '');

  const handleStartSubmit = () => {
    const lat = parseFloat(startLat);
    const lon = parseFloat(startLon);
    if (!isNaN(lat) && !isNaN(lon)) {
      setStartPoint({ lat, lon });
    }
  };

  const handleEndSubmit = () => {
    const lat = parseFloat(endLat);
    const lon = parseFloat(endLon);
    if (!isNaN(lat) && !isNaN(lon)) {
      setEndPoint({ lat, lon });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground uppercase tracking-wider">
        <Navigation className="w-4 h-4 text-primary" />
        <span>Mission Input</span>
      </div>

      {/* Start Point */}
      <div className="space-y-2">
        <Label className="text-xs text-foreground-muted">Start Point</Label>
        <div className="flex gap-2">
          <Input
            placeholder="Lat"
            value={startPoint?.lat.toFixed(6) || startLat}
            onChange={(e) => setStartLat(e.target.value)}
            onBlur={handleStartSubmit}
            className="font-mono text-sm bg-input border-border"
          />
          <Input
            placeholder="Lon"
            value={startPoint?.lon.toFixed(6) || startLon}
            onChange={(e) => setStartLon(e.target.value)}
            onBlur={handleStartSubmit}
            className="font-mono text-sm bg-input border-border"
          />
          <Button
            variant={mapMode === 'set-start' ? 'default' : 'outline'}
            size="icon"
            onClick={() => setMapMode(mapMode === 'set-start' ? 'idle' : 'set-start')}
            className="shrink-0"
            title="Click map to set"
          >
            <MapPin className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* End Point */}
      <div className="space-y-2">
        <Label className="text-xs text-foreground-muted">End Point</Label>
        <div className="flex gap-2">
          <Input
            placeholder="Lat"
            value={endPoint?.lat.toFixed(6) || endLat}
            onChange={(e) => setEndLat(e.target.value)}
            onBlur={handleEndSubmit}
            className="font-mono text-sm bg-input border-border"
          />
          <Input
            placeholder="Lon"
            value={endPoint?.lon.toFixed(6) || endLon}
            onChange={(e) => setEndLon(e.target.value)}
            onBlur={handleEndSubmit}
            className="font-mono text-sm bg-input border-border"
          />
          <Button
            variant={mapMode === 'set-end' ? 'destructive' : 'outline'}
            size="icon"
            onClick={() => setMapMode(mapMode === 'set-end' ? 'idle' : 'set-end')}
            className="shrink-0"
            title="Click map to set"
          >
            <MapPin className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Waypoints */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-xs text-foreground-muted">Waypoints</Label>
          <Button
            variant={mapMode === 'add-waypoint' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setMapMode(mapMode === 'add-waypoint' ? 'idle' : 'add-waypoint')}
            className="h-7 text-xs"
          >
            <Plus className="w-3 h-3 mr-1" />
            Add Waypoint
          </Button>
        </div>

        {waypoints.length > 0 ? (
          <div className="space-y-1">
            {waypoints.map((wp, index) => (
              <div
                key={wp.id}
                className="flex items-center gap-2 p-2 bg-muted/50 rounded text-xs font-mono"
              >
                <span className="w-5 h-5 flex items-center justify-center bg-primary text-primary-foreground rounded-full text-[10px] font-bold">
                  {index + 1}
                </span>
                <span className="flex-1 truncate">
                  {wp.lat.toFixed(6)}, {wp.lon.toFixed(6)}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-danger hover:text-danger hover:bg-danger/10"
                  onClick={() => removeWaypoint(wp.id)}
                >
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-foreground-muted italic">
            No waypoints added. Click the map or use the button above.
          </p>
        )}
      </div>
    </div>
  );
};
