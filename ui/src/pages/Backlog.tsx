import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { BacklogCard } from '@/components/backlog/BacklogCard';
import { useBacklogList } from '@/hooks/useApi';
import { ArrowLeft, Loader2, Database } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Backlog = () => {
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const limit = 20;
  const { data, isLoading, error } = useBacklogList(limit, currentPage * limit);

  const entries = data?.entries ?? [];
  const pagination = data?.pagination;

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b p-4 flex items-center justify-between bg-background-panel">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/')}
            className="gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Planner
          </Button>
          <div className="h-6 w-px bg-border" />
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-primary" />
            <h1 className="text-xl font-bold">Planning Backlog</h1>
          </div>
        </div>

        {pagination && (
          <div className="text-sm text-muted-foreground">
            {pagination.total} total requests
          </div>
        )}
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center space-y-3">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
              <p className="text-muted-foreground">Loading backlog...</p>
            </div>
          </div>
        ) : error ? (
          <div className="text-center text-red-500 py-12">
            <p className="font-semibold">Failed to load backlog</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'Unknown error'}
            </p>
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center text-muted-foreground py-12">
            <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-semibold">No planning requests yet</p>
            <p className="text-sm mt-1">
              Create your first tactical plan to see it here!
            </p>
            <Button onClick={() => navigate('/')} className="mt-4">
              Go to Planner
            </Button>
          </div>
        ) : (
          <div className="space-y-4 max-w-6xl mx-auto">
            {entries.map((entry) => (
              <BacklogCard
                key={entry.request_id}
                entry={entry}
                isExpanded={expandedId === entry.request_id}
                onToggle={() =>
                  setExpandedId(expandedId === entry.request_id ? null : entry.request_id)
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {pagination && pagination.total > limit && (
        <div className="border-t p-4 flex justify-center items-center gap-4 bg-background-panel">
          <Button
            onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
            disabled={currentPage === 0}
            variant="outline"
          >
            Previous
          </Button>

          <span className="text-sm text-muted-foreground">
            Page {currentPage + 1} of {Math.ceil(pagination.total / limit)}
          </span>

          <Button
            onClick={() => setCurrentPage((p) => p + 1)}
            disabled={!pagination.has_more}
            variant="outline"
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
};
