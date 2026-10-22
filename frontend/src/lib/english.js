/** English-only guard for headlines (the backend filters too; this is a second safety net). */
export function isEnglish(text = '') {
  const letters = text.match(/\p{L}/gu)
  if (!letters || letters.length === 0) return false
  const latin = text.match(/\p{Script=Latin}/gu)?.length ?? 0
  return latin / letters.length >= 0.95
}
