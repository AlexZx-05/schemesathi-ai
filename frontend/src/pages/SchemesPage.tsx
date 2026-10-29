import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  RotateCcw,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { SchemeCard } from "../components/schemes/SchemeCard";
import { useSavedSchemes } from "../context/SavedSchemesContext";
import { schemeService } from "../lib/schemes/service";
import { filterSchemes, type SchemeSort } from "../lib/schemes/filterSchemes";
import {
  beneficiaryGroups,
  schemeCategories,
  type Scheme,
} from "../lib/schemes/types";

type LoadState = "loading" | "success" | "error";

export function SchemesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [category, setCategory] = useState("");
  const [beneficiary, setBeneficiary] = useState("");
  const [governmentLevel, setGovernmentLevel] = useState("");
  const [sort, setSort] = useState<SchemeSort>("featured");
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const { savedSchemeIds, storageError } = useSavedSchemes();

  useEffect(() => {
    const controller = new AbortController();
    setLoadState("loading");
    setLoadError(null);

    schemeService
      .getSchemes()
      .then((loadedSchemes) => {
        if (!controller.signal.aborted) {
          setSchemes(loadedSchemes);
          setLoadState("success");
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setLoadError(
            error instanceof Error
              ? error.message
              : "We could not load the scheme catalogue. Please try again.",
          );
          setLoadState("error");
        }
      });

    return () => controller.abort();
  }, [reloadKey]);

  useEffect(() => {
    const nextParams = new URLSearchParams(searchParams);
    if (query.trim()) {
      nextParams.set("q", query.trim());
    } else {
      nextParams.delete("q");
    }
    if (nextParams.toString() !== searchParams.toString()) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [query, searchParams, setSearchParams]);

  const visibleSchemes = useMemo(
    () =>
      filterSchemes(schemes, {
        query,
        category,
        beneficiary,
        governmentLevel,
        sort,
      }),
    [schemes, query, category, beneficiary, governmentLevel, sort],
  );

  function clearFilters() {
    setQuery("");
    setCategory("");
    setBeneficiary("");
    setGovernmentLevel("");
    setSort("featured");
  }

  return (
    <section aria-labelledby="schemes-title" className="discovery-page">
      <div className="discovery-heading">
        <div>
          <p className="eyebrow">Scheme discovery</p>
          <h1 className="page-title" id="schemes-title">
            Explore Government Schemes
          </h1>
          <p className="page-intro">
            Search scheme records by topic, audience, and government level.
          </p>
        </div>
        <a
          className="official-source-link"
          href="https://www.india.gov.in/"
          rel="noreferrer"
          target="_blank"
        >
          National Portal of India
          <ArrowUpRight aria-hidden="true" size={16} />
        </a>
      </div>

      <aside aria-label="Catalogue review notice" className="source-review-notice">
        <span aria-hidden="true" className="source-review-notice__icon">
          i
        </span>
        <p>
          <strong>Official sources first.</strong> Only records with a reviewed
          official source are published. Confirm current details with the
          issuing authority before acting.
        </p>
      </aside>

      <div className="discovery-search">
        <Search aria-hidden="true" size={20} />
        <label className="visually-hidden" htmlFor="scheme-search">
          Search scheme names, topics, and beneficiaries
        </label>
        <input
          autoComplete="off"
          id="scheme-search"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by scheme, topic, or beneficiary..."
          type="search"
          value={query}
        />
        {query && (
          <button
            aria-label="Clear search"
            className="icon-button"
            onClick={() => setQuery("")}
            type="button"
          >
            <RotateCcw aria-hidden="true" size={17} />
          </button>
        )}
      </div>

      <div aria-label="Scheme filters" className="filter-panel">
        <div className="filter-panel-heading">
          <span>
            <SlidersHorizontal aria-hidden="true" size={17} />
            Refine results
          </span>
          <button className="filter-reset" onClick={clearFilters} type="button">
            Clear filters
          </button>
        </div>
        <div className="filter-grid">
          <label className="filter-field">
            <span>Category</span>
            <select
              onChange={(event) => setCategory(event.target.value)}
              value={category}
            >
              <option value="">All categories</option>
              {schemeCategories.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Beneficiary</span>
            <select
              onChange={(event) => setBeneficiary(event.target.value)}
              value={beneficiary}
            >
              <option value="">All beneficiaries</option>
              {beneficiaryGroups.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Government level</span>
            <select
              onChange={(event) => setGovernmentLevel(event.target.value)}
              value={governmentLevel}
            >
              <option value="">All levels</option>
              <option value="Central">Central</option>
              <option value="State">State</option>
              <option value="Local">Local</option>
            </select>
          </label>
          <label className="filter-field">
            <span>Sort by</span>
            <select
              onChange={(event) => setSort(event.target.value as SchemeSort)}
              value={sort}
            >
              <option value="featured">Featured schemes</option>
              <option value="name-asc">Name: A to Z</option>
              <option value="name-desc">Name: Z to A</option>
            </select>
          </label>
        </div>
      </div>

      {storageError && (
        <p className="inline-error" role="alert">
          {storageError}
        </p>
      )}

      {loadState === "loading" && (
        <div aria-label="Loading scheme records" className="scheme-grid">
          {Array.from({ length: 6 }, (_, index) => (
            <div aria-hidden="true" className="scheme-skeleton" key={index} />
          ))}
          <p aria-live="polite" className="visually-hidden">
            Loading verified scheme records
          </p>
        </div>
      )}

      {loadState === "error" && (
        <div className="discovery-state discovery-state--error" role="alert">
          <span aria-hidden="true" className="empty-state-icon">
            !
          </span>
          <h2>We couldn’t load scheme records</h2>
          <p>{loadError}</p>
          <button
            className="button button--primary"
            onClick={() => setReloadKey((current) => current + 1)}
            type="button"
          >
            Try again
          </button>
        </div>
      )}

      {loadState === "success" && (
        <>
          <div className="results-summary" aria-live="polite">
            <p>
              <strong>{visibleSchemes.length}</strong>{" "}
              {visibleSchemes.length === 1 ? "scheme" : "schemes"} shown
              {savedSchemeIds.length > 0 && (
                <span> · {savedSchemeIds.length} saved</span>
              )}
            </p>
          </div>
          {visibleSchemes.length > 0 ? (
            <div className="scheme-grid">
              {visibleSchemes.map((scheme) => (
                <SchemeCard key={scheme.id} scheme={scheme} />
              ))}
            </div>
          ) : (
            <div className="discovery-state">
              <span aria-hidden="true" className="empty-state-icon">
                <Search size={24} />
              </span>
              <h2>
                {schemes.length === 0
                  ? "No reviewed schemes are published yet"
                  : "No matching schemes"}
              </h2>
              <p>
                {schemes.length === 0
                  ? "We publish scheme information only after it has been checked against an official source. Check the National Portal of India for current information in the meantime."
                  : "Try a different search term or clear one or more filters."}
              </p>
              {schemes.length === 0 && (
                <a
                  className="button button--secondary"
                  href="https://www.india.gov.in/"
                  rel="noreferrer"
                  target="_blank"
                >
                  Visit National Portal of India
                  <ArrowUpRight aria-hidden="true" size={16} />
                </a>
              )}
              <button
                className="button button--secondary"
                onClick={clearFilters}
                type="button"
              >
                Clear search and filters
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
