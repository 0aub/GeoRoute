import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { JsonViewer } from './JsonViewer';
import type { GeminiRequest } from '@/types';
import { Clock, Sparkles, Image as ImageIcon } from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface GeminiRequestCardProps {
  request: GeminiRequest;
  index: number;
}

const stageLabels: Record<string, string> = {
  stage1_initial_routes: 'Stage 1: Initial Routes',
  stage2_refine_waypoints: 'Stage 2: Refine Waypoints',
  stage3_score_routes: 'Stage 3: Score Routes',
  stage4_final_classification: 'Stage 4: Final Classification',
};

const stageColors: Record<string, string> = {
  stage1_initial_routes: 'bg-blue-500',
  stage2_refine_waypoints: 'bg-purple-500',
  stage3_score_routes: 'bg-yellow-500',
  stage4_final_classification: 'bg-green-500',
};

export const GeminiRequestCard = ({ request, index }: GeminiRequestCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <Card className="p-3 bg-secondary/30">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-purple-500" />
          <span className="font-semibold text-sm">
            {stageLabels[request.stage] || request.stage}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {request.image_included && (
            <Badge variant="secondary" className="text-xs">
              <ImageIcon className="w-3 h-3 mr-1" />
              Image
            </Badge>
          )}
          <Badge className={stageColors[request.stage] || 'bg-gray-500'}>
            Stage {index}
          </Badge>
        </div>
      </div>

      <div className="space-y-2 text-xs">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Clock className="w-3 h-3" />
          <span>{new Date(request.timestamp).toLocaleString()}</span>
        </div>

        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <CollapsibleTrigger className="flex items-center gap-2 text-primary hover:underline">
            <span>View Prompt & Response</span>
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </CollapsibleTrigger>

          <CollapsibleContent className="mt-2 space-y-2">
            <div>
              <span className="font-semibold">Prompt:</span>
              <div className="bg-secondary p-2 rounded mt-1 max-h-40 overflow-auto">
                <pre className="whitespace-pre-wrap text-xs">{request.prompt}</pre>
              </div>
            </div>

            <div>
              <span className="font-semibold">Response:</span>
              <JsonViewer data={JSON.parse(request.response)} maxHeight="300px" />
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </Card>
  );
};
