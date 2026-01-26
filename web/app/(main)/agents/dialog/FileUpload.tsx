'use client';

import { useState, useRef } from 'react';
import styles from './dialog.module.css';

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
  maxFiles?: number;
  acceptedTypes?: string;
}

export function FileUpload({
  onFilesSelected,
  disabled = false,
  maxFiles = 5,
  acceptedTypes = 'image/*,audio/*,.pdf,.doc,.docx,.txt',
}: FileUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    
    if (files.length + selectedFiles.length > maxFiles) {
      alert(`最多只能上传 ${maxFiles} 个文件`);
      return;
    }

    const newFiles = [...selectedFiles, ...files];
    setSelectedFiles(newFiles);
    onFilesSelected(newFiles);
  };

  const handleRemoveFile = (index: number) => {
    const newFiles = selectedFiles.filter((_, i) => i !== index);
    setSelectedFiles(newFiles);
    onFilesSelected(newFiles);
  };

  const handleClearAll = () => {
    setSelectedFiles([]);
    onFilesSelected([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (type: string): string => {
    if (type.startsWith('image/')) return '🖼️';
    if (type.startsWith('audio/')) return '🎵';
    if (type.startsWith('video/')) return '🎬';
    if (type.includes('pdf')) return '📄';
    if (type.includes('word') || type.includes('document')) return '📝';
    if (type.includes('excel') || type.includes('spreadsheet')) return '📊';
    return '📎';
  };

  return (
    <div className={styles.fileUploadContainer}>
      <div className={styles.fileUploadActions}>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes}
          onChange={handleFileSelect}
          disabled={disabled}
          style={{ display: 'none' }}
          id="file-upload-input"
        />
        <label
          htmlFor="file-upload-input"
          className={`${styles.fileUploadButton} ${disabled ? styles.disabled : ''}`}
        >
          📎 选择文件
        </label>
        {selectedFiles.length > 0 && (
          <button
            type="button"
            onClick={handleClearAll}
            className={styles.fileClearButton}
            disabled={disabled}
          >
            清空
          </button>
        )}
        <span className={styles.fileUploadHint}>
          {selectedFiles.length}/{maxFiles} 个文件
        </span>
      </div>

      {selectedFiles.length > 0 && (
        <div className={styles.fileList}>
          {selectedFiles.map((file, index) => (
            <div key={index} className={styles.fileItem}>
              <span className={styles.fileIcon}>{getFileIcon(file.type)}</span>
              <div className={styles.fileInfo}>
                <div className={styles.fileName}>{file.name}</div>
                <div className={styles.fileSize}>{formatFileSize(file.size)}</div>
              </div>
              <button
                type="button"
                onClick={() => handleRemoveFile(index)}
                className={styles.fileRemoveButton}
                disabled={disabled}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
