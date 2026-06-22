import { formatDate, formatFileSize } from '@/utils/utils';
import {
  EFileStatus,
} from '../types/common';
import type {
  FileStatus,
  IStatusCount,
} from '../types/common';

export function ensureArray<T>(value: T | T[] | undefined | null): T[] {
  if (value === undefined || value === null) return [];
  return Array.isArray(value) ? value : [value];
}

export function ensureString(value: unknown, fallback = ''): string {
  if (value === undefined || value === null) return fallback;
  return String(value);
}

export function ensureNumber(value: unknown, fallback = 0): number {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

export function ensureBoolean(value: unknown, fallback = false): boolean {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') return value.toLowerCase() === 'true';
  if (typeof value === 'number') return value !== 0;
  return fallback;
}

export function normalizeStatusCount(raw: Record<string, unknown> | undefined): IStatusCount {
  return {
    green: ensureNumber(raw?.green, 0),
    gray: ensureNumber(raw?.gray, 0),
    yellow: ensureNumber(raw?.yellow, 0),
    red: ensureNumber(raw?.red, 0),
  };
}

export function normalizeFileStatus(status: unknown): FileStatus {
  const s = ensureString(status, 'gray');
  const valid: EFileStatus[] = [
    EFileStatus.SUCCESS,
    EFileStatus.PARSING,
    EFileStatus.WAITING,
    EFileStatus.FAILED,
    EFileStatus.LOADING,
  ];
  return (valid.includes(s as EFileStatus) ? s : EFileStatus.WAITING) as FileStatus;
}

export function normalizeTimestamp(timestamp: unknown): string {
  return formatDate(ensureString(timestamp));
}

export function normalizeBytes(bytes: unknown): { raw: number; display: string } {
  const raw = ensureNumber(bytes, 0);
  return {
    raw,
    display: formatFileSize(raw),
  };
}

export function parseRemarkMessage(msg: string | undefined, status: FileStatus): string | Record<string, string> {
  if (status !== EFileStatus.SUCCESS) {
    return ensureString(msg);
  }
  try {
    const parsed = JSON.parse(ensureString(msg, '{}'));
    return typeof parsed === 'object' && parsed !== null ? parsed : ensureString(msg);
  } catch {
    return ensureString(msg);
  }
}

export function normalizeTags(tags: unknown): string[] {
  if (Array.isArray(tags)) return tags.map(t => ensureString(t));
  if (typeof tags === 'string') return tags ? [tags] : [];
  return [];
}

export function normalizeKbIds(kbIds: unknown): { raw: string[]; display: string } {
  const arr = ensureArray(kbIds)
    .map(id => ensureString(id))
    .filter(Boolean);
  return {
    raw: arr,
    display: arr.join('\n'),
  };
}
