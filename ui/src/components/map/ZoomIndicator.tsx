import { useEffect, useState } from 'react';
import type L from 'leaflet';
import { ZoomIn } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface ZoomIndicatorProps {
  map: L.Map | null;
}

export const ZoomIndicator = ({ map }: ZoomIndicatorProps) => {
  const [zoom, setZoom] = useState(map?.getZoom() ?? 6);

  useEffect(() => {
    if (!map) return;

    const updateZoom = () => setZoom(map.getZoom());

    // Set initial zoom
    updateZoom();

    // Listen for zoom changes
    map.on('zoomend', updateZoom);

    return () => {
      map.off('zoomend', updateZoom);
    };
  }, [map]);

  // Tactical planning range: 11-15
  const isTactical = zoom >= 11 && zoom <= 15;
  const isTooFar = zoom < 11;
  const isTooClose = zoom > 15;

  return (
    <div className="absolute top-4 left-4 bg-background border rounded-lg px-3 py-2 shadow-lg z-[1000]">
      <div className="flex items-center gap-2">
        <ZoomIn className="w-4 h-4 text-muted-foreground" />
        <span className="font-mono font-semibold">{zoom}</span>
        {isTactical && (
          <Badge variant="default" className="bg-green-600">
            TACTICAL
          </Badge>
        )}
        {isTooFar && (
          <Badge variant="secondary">
            TOO FAR
          </Badge>
        )}
        {isTooClose && (
          <Badge variant="destructive">
            TOO CLOSE
          </Badge>
        )}
      </div>
      {isTooFar && (
        <p className="text-xs text-muted-foreground mt-1">
          Zoom in for tactical planning (11-15)
        </p>
      )}
      {isTooClose && (
        <p className="text-xs text-muted-foreground mt-1">
          Zoom out for better area view
        </p>
      )}
      {isTactical && (
        <p className="text-xs text-green-600 mt-1">
          Optimal range for tactical operations
        </p>
      )}
    </div>
  );
};
