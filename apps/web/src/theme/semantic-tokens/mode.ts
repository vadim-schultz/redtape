/** Pair a light value with its `_dark` counterpart. */
export function mode(base: string, dark: string) {
  return { value: { base, _dark: dark } };
}
