import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useAuth } from "./AuthContext";
import { guidanceService } from "../lib/guidance";
import type { ReactNode } from "react";

interface SavedSchemesContextValue {
  savedSchemeIds: string[];
  storageError: string | null;
  toggleSavedScheme: (schemeId: string) => Promise<void>;
}

interface SavedState {
  ids: string[];
  error: string | null;
}

const SavedSchemesContext = createContext<SavedSchemesContextValue | null>(
  null,
);

export function SavedSchemesProvider({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const [savedState, setSavedState] = useState<SavedState>({ ids: [], error: null });

  useEffect(() => {
    let active = true;
    if (status !== "authenticated") {
      setSavedState({ ids: [], error: null });
      return () => { active = false; };
    }
    guidanceService.listSaved().then((saved) => {
      if (active) setSavedState({ ids: saved.map((item) => item.scheme_id), error: null });
    }).catch(() => {
      if (active) setSavedState({ ids: [], error: "Saved schemes could not be loaded." });
    });
    return () => { active = false; };
  }, [status]);

  const toggleSavedScheme = useCallback(async (schemeId: string) => {
    if (status !== "authenticated") {
      setSavedState((current) => ({ ...current, error: "Sign in to save schemes." }));
      return;
    }
    try {
      if (savedState.ids.includes(schemeId)) {
        await guidanceService.unsave(schemeId);
        setSavedState((current) => ({ ids: current.ids.filter((id) => id !== schemeId), error: null }));
      } else {
        await guidanceService.save(schemeId);
        setSavedState((current) => ({ ids: [...current.ids, schemeId], error: null }));
      }
    } catch {
      setSavedState((current) => ({ ...current, error: "Could not update your saved schemes." }));
    }
  }, [savedState.ids, status]);

  const value = useMemo(
    () => ({
      savedSchemeIds: savedState.ids,
      storageError: savedState.error,
      toggleSavedScheme,
    }),
    [savedState, toggleSavedScheme],
  );

  return (
    <SavedSchemesContext.Provider value={value}>
      {children}
    </SavedSchemesContext.Provider>
  );
}

export function useSavedSchemes() {
  const context = useContext(SavedSchemesContext);
  if (!context) {
    throw new Error(
      "useSavedSchemes must be used within SavedSchemesProvider.",
    );
  }
  return context;
}
