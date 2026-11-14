export function formatYear(y: number): string {
  return y < 0 ? `前 ${-y}` : `${y}`;
}
