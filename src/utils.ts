/**
 * d3-zoom filter that lets plain wheel events scroll the notebook;
 * zooming then needs Ctrl/Cmd+wheel (or a pinch gesture).
 */
export function wheelZoomFilter(event: any): boolean {
  return event.type === 'wheel'
    ? event.ctrlKey || event.metaKey
    : !event.button;
}

/**
 * Parse renderer data that may arrive as a JSON string (e.g. from a file).
 */
export function parseData<T>(raw: unknown): T {
  return (typeof raw === 'string' ? JSON.parse(raw) : raw) as T;
}
