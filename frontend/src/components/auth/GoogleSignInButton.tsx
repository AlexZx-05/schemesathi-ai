import { useEffect, useRef, useState } from "react";
import { Chrome } from "lucide-react";

interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleIdentityServices {
  accounts: {
    id: {
      initialize: (options: {
        client_id: string;
        callback: (response: GoogleCredentialResponse) => void;
      }) => void;
      renderButton: (
        element: HTMLElement,
        options: {
          theme: "outline";
          size: "large";
          text: "continue_with";
          shape: "rectangular";
          width: number;
        },
      ) => void;
    };
  };
}

declare global {
  interface Window {
    google?: GoogleIdentityServices;
  }
}

interface GoogleSignInButtonProps {
  disabled?: boolean;
  onCredential: (credential: string) => void | Promise<void>;
}

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim() ?? "";
const googleScriptUrl = "https://accounts.google.com/gsi/client";

export function GoogleSignInButton({
  disabled = false,
  onCredential,
}: GoogleSignInButtonProps) {
  const buttonHost = useRef<HTMLDivElement>(null);
  const credentialHandler = useRef(onCredential);
  const [scriptError, setScriptError] = useState(false);

  credentialHandler.current = onCredential;

  useEffect(() => {
    if (!googleClientId) return;

    let active = true;
    const renderGoogleButton = () => {
      if (!active || !buttonHost.current || !window.google) return;
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: ({ credential }) => credentialHandler.current(credential),
      });
      window.google.accounts.id.renderButton(buttonHost.current, {
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        width: Math.min(400, Math.floor(buttonHost.current.clientWidth)),
      });
    };

    const existingScript = document.querySelector<HTMLScriptElement>(
      `script[src="${googleScriptUrl}"]`,
    );
    if (window.google) {
      renderGoogleButton();
    } else {
      const script = existingScript ?? document.createElement("script");
      const handleLoad = () => renderGoogleButton();
      const handleError = () => {
        if (active) setScriptError(true);
      };

      script.addEventListener("load", handleLoad);
      script.addEventListener("error", handleError);
      if (!existingScript) {
        script.src = googleScriptUrl;
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
      }

      return () => {
        active = false;
        script.removeEventListener("load", handleLoad);
        script.removeEventListener("error", handleError);
      };
    }

    return () => {
      active = false;
    };
  }, []);

  if (!googleClientId) {
    return (
      <div className="google-signin">
        <button className="auth-social-button" disabled type="button">
          <Chrome aria-hidden="true" size={19} />
          Continue with Google
        </button>
        <span className="google-signin-note">
          Google sign-in is unavailable until it is configured.
        </span>
      </div>
    );
  }

  return (
    <div className="google-signin">
      <div
        aria-label="Continue with Google"
        aria-disabled={disabled}
        className={`google-signin-button${disabled ? " is-disabled" : ""}`}
        ref={buttonHost}
      />
      {scriptError && (
        <span className="google-signin-note" role="alert">
          Google sign-in could not load. Check your connection and try again.
        </span>
      )}
    </div>
  );
}
