import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Image as ImageIcon } from 'lucide-react';

interface ImageGalleryProps {
  satellite?: string;
  terrain?: string;
}

export const ImageGallery = ({ satellite, terrain }: ImageGalleryProps) => {
  const [selectedImage, setSelectedImage] = useState<{
    src: string;
    title: string;
  } | null>(null);

  if (!satellite && !terrain) {
    return (
      <div className="text-sm text-muted-foreground">No images available</div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        {satellite && (
          <Card
            className="p-2 cursor-pointer hover:ring-2 hover:ring-primary transition"
            onClick={() =>
              setSelectedImage({
                src: `data:image/png;base64,${satellite}`,
                title: 'Satellite Image',
              })
            }
          >
            <div className="aspect-square bg-secondary rounded overflow-hidden mb-2">
              <img
                src={`data:image/png;base64,${satellite}`}
                alt="Satellite"
                className="w-full h-full object-cover"
              />
            </div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <ImageIcon className="w-3 h-3" />
              <span>Satellite Image</span>
            </div>
          </Card>
        )}

        {terrain && (
          <Card
            className="p-2 cursor-pointer hover:ring-2 hover:ring-primary transition"
            onClick={() =>
              setSelectedImage({
                src: `data:image/png;base64,${terrain}`,
                title: 'Terrain Image',
              })
            }
          >
            <div className="aspect-square bg-secondary rounded overflow-hidden mb-2">
              <img
                src={`data:image/png;base64,${terrain}`}
                alt="Terrain"
                className="w-full h-full object-cover"
              />
            </div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <ImageIcon className="w-3 h-3" />
              <span>Terrain Image</span>
            </div>
          </Card>
        )}
      </div>

      {/* Full-size image modal */}
      <Dialog
        open={!!selectedImage}
        onOpenChange={(open) => !open && setSelectedImage(null)}
      >
        <DialogContent className="max-w-4xl">
          <DialogTitle>{selectedImage?.title}</DialogTitle>
          {selectedImage && (
            <div className="w-full">
              <img
                src={selectedImage.src}
                alt={selectedImage.title}
                className="w-full h-auto rounded"
              />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};
