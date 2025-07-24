import React, { useState, useRef } from 'react';
import styles from '../styles/DocumentUpload.module.css';

interface DocumentUploadProps {
  onUpload: (file: File) => Promise<void>;
  acceptedFormats?: string;
  maxSizeMB?: number;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ 
  onUpload, 
  acceptedFormats = '.docx,.md', 
  maxSizeMB = 10 
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    setError(null);
    
    // Check file size
    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File size exceeds ${maxSizeMB}MB limit`);
      return;
    }
    
    // Check file type
    const fileExtension = file.name.split('.').pop()?.toLowerCase();
    const acceptedExtensions = acceptedFormats.split(',').map(ext => 
      ext.startsWith('.') ? ext.substring(1) : ext
    );
    
    if (!fileExtension || !acceptedExtensions.includes(fileExtension)) {
      setError(`File type not supported. Accepted formats: ${acceptedFormats}`);
      return;
    }
    
    setFile(file);
  };

  const handleUpload = async () => {
    if (!file) return;
    
    try {
      setUploading(true);
      await onUpload(file);
      setFile(null);
      setError(null);
    } catch (err) {
      setError('Upload failed. Please try again.');
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className={styles.container}>
      <div 
        className={`${styles.dropzone} ${isDragging ? styles.dragging : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleBrowseClick}
      >
        <input 
          type="file" 
          ref={fileInputRef}
          onChange={handleFileChange}
          accept={acceptedFormats}
          style={{ display: 'none' }}
        />
        
        {file ? (
          <div className={styles.fileInfo}>
            <p className={styles.fileName}>{file.name}</p>
            <p className={styles.fileSize}>{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
          </div>
        ) : (
          <div className={styles.placeholder}>
            <p>Drag & drop a document here or click to browse</p>
            <p className={styles.supportedFormats}>
              Supported formats: .DOCX (with diagram extraction), .MD
            </p>
            <p className={styles.maxSize}>Max size: {maxSizeMB}MB</p>
          </div>
        )}
      </div>
      
      {error && <p className={styles.error}>{error}</p>}
      
      {file && (
        <button 
          className={styles.uploadButton}
          onClick={handleUpload}
          disabled={uploading}
        >
          {uploading ? 'Uploading...' : 'Upload Document'}
        </button>
      )}
    </div>
  );
};

export default DocumentUpload;