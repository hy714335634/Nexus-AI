const DATE_TIME_FORMATTER = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium',
  timeStyle: 'short',
});

const RELATIVE_TIME_FORMATTER = new Intl.RelativeTimeFormat('zh-CN', {
  numeric: 'auto',
});

export function formatDateTime(value?: string | null): string {
  if (!value) {
    return '未知';
  }

  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return value;
  }

  return DATE_TIME_FORMATTER.format(date);
}

export function formatDuration(seconds?: number | null): string {
  if (seconds == null) {
    return '未知';
  }

  const totalSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}小时${minutes}分`;
  }

  if (minutes > 0) {
    return `${minutes}分${secs}秒`;
  }

  return `${secs}秒`;
}

export function formatRelativeTime(value?: string | null): string {
  if (!value) {
    return '未知';
  }

  const date = new Date(value);
  const now = Date.now();
  const diffMs = date.getTime() - now;

  if (Number.isNaN(diffMs)) {
    return '未知';
  }

  const diffSeconds = Math.round(diffMs / 1000);
  const absSeconds = Math.abs(diffSeconds);

  if (absSeconds < 60) {
    return RELATIVE_TIME_FORMATTER.format(diffSeconds, 'second');
  }

  const diffMinutes = Math.round(diffSeconds / 60);
  const absMinutes = Math.abs(diffMinutes);
  if (absMinutes < 60) {
    return RELATIVE_TIME_FORMATTER.format(diffMinutes, 'minute');
  }

  const diffHours = Math.round(diffMinutes / 60);
  const absHours = Math.abs(diffHours);
  if (absHours < 24) {
    return RELATIVE_TIME_FORMATTER.format(diffHours, 'hour');
  }

  const diffDays = Math.round(diffHours / 24);
  return RELATIVE_TIME_FORMATTER.format(diffDays, 'day');
}
