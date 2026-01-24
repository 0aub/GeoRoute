import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { JsonViewer } from './JsonViewer';
import type { APICall } from '@/types';
import { Clock, Server } from 'lucide-react';

interface ApiCallCardProps {
  call: APICall;
  index: number;
}

export const ApiCallCard = ({ call, index }: ApiCallCardProps) => {
  const serviceColor: Record<string, string> = {
    google_maps: 'bg-blue-500',
    gemini: 'bg-purple-500',
    osrm: 'bg-green-500',
    ors: 'bg-orange-500',
  };

  return (
    <Card className="p-3 bg-secondary/30">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-muted-foreground" />
          <span className="font-semibold text-sm">API Call #{index + 1}</span>
        </div>
        <Badge className={serviceColor[call.service] || 'bg-gray-500'}>
          {call.service}
        </Badge>
      </div>

      <div className="space-y-2 text-xs">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Clock className="w-3 h-3" />
          <span>{new Date(call.timestamp).toLocaleString()}</span>
        </div>

        <div>
          <span className="font-semibold">Endpoint: </span>
          <code className="bg-secondary px-1 py-0.5 rounded">{call.endpoint}</code>
        </div>

        <div>
          <span className="font-semibold">Request Parameters:</span>
          <JsonViewer data={call.request_params} maxHeight="200px" />
        </div>

        <div>
          <span className="font-semibold">Response Data:</span>
          <JsonViewer data={call.response_data} maxHeight="200px" />
        </div>
      </div>
    </Card>
  );
};
