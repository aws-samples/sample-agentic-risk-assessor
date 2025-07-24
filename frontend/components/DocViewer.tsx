import React, { useState, useEffect } from 'react';

interface PdfViewerProps {
  pdfContent?: Blob;
  containerHeight?: string;
  displayWidth?: string;
}

const PdfViewer: React.FC<PdfViewerProps> = ( {
  pdfContent,
  containerHeight = '100vh',
  displayWidth = '100%'
}) => {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!pdfContent) return;
    
    const objectUrl = URL.createObjectURL(pdfContent);
    setPdfUrl(objectUrl + '#toolbar=0&navpanes=0&statusbar=0&view=Fit');

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [pdfContent])

  return (
    <div style={{ height: containerHeight, width: displayWidth, border: "1px Solid #FFCC00" }}>
      {pdfUrl ? (
        <iframe src={pdfUrl} width="100%" height="100%" title="PDF Viewer"/>
      ) : (
        <p>Loading PDF...</p>
      )}
    </div>
  );
};
export default PdfViewer;