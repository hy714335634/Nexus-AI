'use client';

import { ReactNode, useEffect } from 'react';
import styles from './modal.module.css';

interface ModalProps {
  readonly open: boolean;
  readonly title?: string;
  readonly description?: string;
  readonly onClose?: () => void;
  readonly footer?: ReactNode;
  readonly children: ReactNode;
}

export function Modal({ open, title, description, onClose, footer, children }: ModalProps) {
  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose?.();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true">
      <div className={styles.dialog}>
        <header className={styles.header}>
          <div>
            {title ? <h2 className={styles.title}>{title}</h2> : null}
            {description ? <p className={styles.description}>{description}</p> : null}
          </div>
          <button type="button" className={styles.closeButton} aria-label="关闭" onClick={onClose}>
            ×
          </button>
        </header>
        <div className={styles.body}>{children}</div>
        {footer ? <footer className={styles.footer}>{footer}</footer> : null}
      </div>
    </div>
  );
}
