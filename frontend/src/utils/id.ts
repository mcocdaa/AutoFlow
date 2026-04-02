export function generateId(): string {
  return (
    "id_" + Date.now().toString(36) + Math.random().toString(36).substr(2, 9)
  );
}
