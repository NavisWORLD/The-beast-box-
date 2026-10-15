'use client';
import type {ReactNode} from 'react';
import styles from './settings-friendly-wrap.module.css';

/**
 * Collapsible wrapper for dense owner/cloud surfaces on family pages.
 * Default open preserves current visibility and tests; families can tuck
 * it away. No state store, no preference key — a second mode toggle would
 * compete with the established progressive-disclosure contract.
 */
export default function SettingsFriendlyWrap({summary,children,open=true}:{summary:string;children:ReactNode;open?:boolean}){
 return <details className={styles.wrap} open={open||undefined}>
  <summary className={styles.summary}>{summary}</summary>
  <div className={styles.body}>{children}</div>
 </details>;
}
