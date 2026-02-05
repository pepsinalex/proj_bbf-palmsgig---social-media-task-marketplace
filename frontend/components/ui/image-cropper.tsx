'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Button } from './button';

export interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ImageCropperProps {
  image: string;
  aspectRatio?: number;
  onCropComplete?: (croppedImage: string) => void;
  onCancel?: () => void;
  className?: string;
}

export function ImageCropper({
  image,
  aspectRatio,
  onCropComplete,
  onCancel,
  className = '',
}: ImageCropperProps) {
  const [crop, setCrop] = useState<CropArea>({ x: 0, y: 0, width: 100, height: 100 });
  const [zoom, setZoom] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      setImageLoaded(true);
      if (aspectRatio) {
        const imgAspect = img.width / img.height;
        if (imgAspect > aspectRatio) {
          const newWidth = (img.height * aspectRatio * 80) / img.width;
          setCrop({ x: (100 - newWidth) / 2, y: 10, width: newWidth, height: 80 });
        } else {
          const newHeight = (img.width / aspectRatio * 80) / img.height;
          setCrop({ x: 10, y: (100 - newHeight) / 2, width: 80, height: newHeight });
        }
      } else {
        setCrop({ x: 10, y: 10, width: 80, height: 80 });
      }
    };
    img.src = image;
    imageRef.current = img;
  }, [image, aspectRatio]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;

      const container = containerRef.current;
      const rect = container.getBoundingClientRect();
      const dx = ((e.clientX - dragStart.x) / rect.width) * 100;
      const dy = ((e.clientY - dragStart.y) / rect.height) * 100;

      setCrop((prev) => {
        const newX = Math.max(0, Math.min(100 - prev.width, prev.x + dx));
        const newY = Math.max(0, Math.min(100 - prev.height, prev.y + dy));
        return { ...prev, x: newX, y: newY };
      });

      setDragStart({ x: e.clientX, y: e.clientY });
    },
    [isDragging, dragStart]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  const handleZoomChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setZoom(parseFloat(e.target.value));
  }, []);

  const getCroppedImage = useCallback(async (): Promise<string | null> => {
    if (!imageRef.current || !canvasRef.current) return null;

    const img = imageRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const scaleX = img.naturalWidth / 100;
    const scaleY = img.naturalHeight / 100;

    const cropX = crop.x * scaleX;
    const cropY = crop.y * scaleY;
    const cropWidth = crop.width * scaleX;
    const cropHeight = crop.height * scaleY;

    canvas.width = cropWidth * zoom;
    canvas.height = cropHeight * zoom;

    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(
      img,
      cropX,
      cropY,
      cropWidth,
      cropHeight,
      0,
      0,
      canvas.width,
      canvas.height
    );

    return canvas.toDataURL('image/jpeg', 0.95);
  }, [crop, zoom]);

  const handleCrop = useCallback(async () => {
    const croppedImage = await getCroppedImage();
    if (croppedImage && onCropComplete) {
      onCropComplete(croppedImage);
    }
  }, [getCroppedImage, onCropComplete]);

  if (!imageLoaded) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <div className="text-center">
          <div className="mb-2 h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-sky-500" />
          <p className="text-sm text-gray-600 dark:text-gray-400">Loading image...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col space-y-4 ${className}`}>
      <div
        ref={containerRef}
        className="relative mx-auto aspect-video w-full max-w-2xl overflow-hidden rounded-lg border border-gray-200 bg-gray-100 dark:border-gray-700 dark:bg-gray-900"
      >
        <img
          src={image}
          alt="Crop preview"
          className="h-full w-full object-contain"
          style={{ transform: `scale(${zoom})` }}
        />

        <div
          className="absolute cursor-move border-2 border-sky-500 bg-black/30"
          style={{
            left: `${crop.x}%`,
            top: `${crop.y}%`,
            width: `${crop.width}%`,
            height: `${crop.height}%`,
          }}
          onMouseDown={handleMouseDown}
        >
          <div className="absolute inset-0 grid grid-cols-3 grid-rows-3">
            {[...Array(9)].map((_, i) => (
              <div key={i} className="border border-white/30" />
            ))}
          </div>

          <div className="absolute -right-2 -top-2 h-4 w-4 rounded-full border-2 border-sky-500 bg-white" />
          <div className="absolute -bottom-2 -left-2 h-4 w-4 rounded-full border-2 border-sky-500 bg-white" />
          <div className="absolute -bottom-2 -right-2 h-4 w-4 rounded-full border-2 border-sky-500 bg-white" />
          <div className="absolute -left-2 -top-2 h-4 w-4 rounded-full border-2 border-sky-500 bg-white" />
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <label htmlFor="zoom-slider" className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Zoom
        </label>
        <input
          id="zoom-slider"
          type="range"
          min="1"
          max="3"
          step="0.1"
          value={zoom}
          onChange={handleZoomChange}
          className="flex-1"
        />
        <span className="text-sm text-gray-600 dark:text-gray-400">{Math.round(zoom * 100)}%</span>
      </div>

      <div className="flex justify-end space-x-3">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="button" onClick={handleCrop}>
          Crop Image
        </Button>
      </div>

      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
