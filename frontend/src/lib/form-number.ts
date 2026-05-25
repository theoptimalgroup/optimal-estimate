/** Map cleared/invalid numeric inputs to numbers for React Hook Form + Zod. */
export function numberFieldOptions(defaultWhenEmpty?: number) {
  return {
    setValueAs: (value: unknown) => {
      if (value === "" || value === null || value === undefined) {
        return defaultWhenEmpty !== undefined ? defaultWhenEmpty : undefined;
      }
      if (typeof value === "number") {
        return Number.isNaN(value) ? (defaultWhenEmpty !== undefined ? defaultWhenEmpty : undefined) : value;
      }
      const parsed = Number(value);
      if (Number.isNaN(parsed)) {
        return defaultWhenEmpty !== undefined ? defaultWhenEmpty : undefined;
      }
      return parsed;
    },
  };
}
