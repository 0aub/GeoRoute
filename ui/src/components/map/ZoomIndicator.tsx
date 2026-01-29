import { useEffect, useState } from 'react';
import type L from 'leaflet';
import { ZoomIn } from 'lucide-react';

interface ZoomIndicatorProps {
  map: L.Map | null;
}

export const ZoomIndicator = ({ map }: ZoomIndicatorProps) => {
  const [zoom, setZoom] = useState(map?.getZoom() ?? 6);

  useEffect(() => {
    if (!map) return;

    const updateZoom = () => setZoom(map.getZoom());
    updateZoom();
    map.on('zoomend', updateZoom);

    return () => {
      map.off('zoomend', updateZoom);
    };
  }, [map]);

  return (
    <div className="absolute top-2 left-2 bg-background/80 border rounded px-1.5 py-0.5 shadow z-[1000]">
      <div className="flex items-center gap-1 text-[10px]">
        <ZoomIn className="w-3 h-3 text-muted-foreground" />
        <span className="font-mono font-semibold">{zoom}</span>
      </div>
    </div>
  );
};
