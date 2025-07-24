import { useState, useRef, useCallback } from 'react';
import styles from '../styles/ZoomableDiagram.module.css';

interface ZoomableDiagramProps {
  src: string;
  alt: string;
  className?: string;
}

export default function ZoomableDiagram({ src, alt, className }: ZoomableDiagramProps) {
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.min(Math.max(scale * delta, 0.5), 3);
    setScale(newScale);
  }, [scale]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  }, [position]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const resetZoom = useCallback(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  }, []);

  const zoomIn = useCallback(() => {
    setScale(prev => Math.min(prev * 1.2, 3));
  }, []);

  const zoomOut = useCallback(() => {
    setScale(prev => Math.max(prev * 0.8, 0.5));
  }, []);

  return (
    <div className={`${styles.zoomContainer} ${className || ''}`}>
      <div className={styles.zoomControls}>
        <button onClick={zoomIn} className={styles.zoomButton} title="Zoom In">
          +
        </button>
        <button onClick={zoomOut} className={styles.zoomButton} title="Zoom Out">
          −
        </button>
        <button onClick={resetZoom} className={styles.resetButton} title="Reset Zoom">
          ⌂
        </button>
        <span className={styles.zoomLevel}>{Math.round(scale * 100)}%</span>
      </div>
      
      <div
        ref={containerRef}
        className={styles.imageContainer}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <img
          src={src}
          alt={alt}
          className={styles.zoomableImage}
          style={{
            transform: `scale(${scale}) translate(${position.x / scale}px, ${position.y / scale}px)`,
            cursor: isDragging ? 'grabbing' : 'grab'
          }}
          draggable={false}
        />
      </div>
    </div>
  );
}