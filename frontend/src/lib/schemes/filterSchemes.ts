import type { Scheme } from "./types";

export type SchemeSort = "featured" | "name-asc" | "name-desc";

export interface SchemeFilters {
  query: string;
  category: string;
  beneficiary: string;
  governmentLevel: string;
  sort: SchemeSort;
}

export function filterSchemes(
  schemes: Scheme[],
  filters: SchemeFilters,
): Scheme[] {
  const normalizedQuery = filters.query.trim().toLocaleLowerCase();

  const matches = schemes.filter((scheme) => {
    const matchesQuery =
      !normalizedQuery ||
      [
        scheme.name,
        scheme.shortDescription,
        scheme.category,
        scheme.governmentLevel,
        ...scheme.beneficiaries,
        ...scheme.keywords,
      ]
        .join(" ")
        .toLocaleLowerCase()
        .includes(normalizedQuery);

    return (
      matchesQuery &&
      (!filters.category || scheme.category === filters.category) &&
      (!filters.beneficiary ||
        scheme.beneficiaries.some(
          (group) => group === filters.beneficiary,
        )) &&
      (!filters.governmentLevel ||
        scheme.governmentLevel === filters.governmentLevel)
    );
  });

  if (filters.sort === "name-asc") {
    return matches.sort((left, right) => left.name.localeCompare(right.name));
  }

  if (filters.sort === "name-desc") {
    return matches.sort((left, right) => right.name.localeCompare(left.name));
  }

  return matches;
}
