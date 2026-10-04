export async function resolve(specifier, context, nextResolve) {
  const relative = specifier.startsWith("./") || specifier.startsWith("../");
  const bare = relative && !/\.[a-z0-9]+$/i.test(specifier);
  if (bare) {
    try {
      return await nextResolve(specifier + ".ts", context);
    } catch {
      return nextResolve(specifier, context);
    }
  }
  return nextResolve(specifier, context);
}
