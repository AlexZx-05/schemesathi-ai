export const schemeCategories = [
  "Education",
  "Agriculture",
  "Employment",
  "Healthcare",
  "Women and child welfare",
  "Housing",
  "Financial assistance",
] as const;

export type SchemeCategory = (typeof schemeCategories)[number];

export const beneficiaryGroups = [
  "Students",
  "Farmers",
  "Job seekers",
  "Women",
  "Children",
  "Families",
  "Low-income households",
  "Persons with disabilities",
  "Senior citizens",
  "Other",
] as const;

export type BeneficiaryGroup = (typeof beneficiaryGroups)[number];
export type GovernmentLevel = "Central" | "State" | "Local" | "Unknown";
export type SchemeSourceStatus =
  | "unverified"
  | "verified"
  | "unavailable"
  | "stale";

export interface SchemeSource {
  url: string;
  title: string | null;
  status: SchemeSourceStatus;
  lastVerifiedAt: string | null;
}

export interface Scheme {
  id: string;
  name: string;
  shortDescription: string;
  category: SchemeCategory | null;
  beneficiaries: BeneficiaryGroup[];
  governmentLevel: GovernmentLevel;
  keywords: string[];
  benefits: string[];
  eligibilityCriteria: string[];
  requiredDocuments: string[];
  applicationProcedure: string[];
  officialSource: string | null;
  lastVerifiedDate: string | null;
  dataStatus: "verified";
  sources?: SchemeSource[];
}
