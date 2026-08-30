/**
 * One-time notice explaining what this deployment is.
 *
 * Shown once per browser: the demo carries synthetic freight, sends nothing
 * externally, and some screens are labelled design previews. Dismissal is a
 * per-viewer convenience in localStorage; failure to read it just shows the
 * notice again, which is the safe direction.
 */

import { useState } from "react";

import "./SandboxNotice.css";

const STORAGE_KEY = "relayops.sandboxNoticeDismissed";

function readDismissed(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function SandboxNotice() {
  const [dismissed, setDismissed] = useState(readDismissed);

  if (dismissed) return null;

  const dismiss = () => {
    setDismissed(true);
    try {
      window.localStorage.setItem(STORAGE_KEY, "true");
    } catch {
      // Nothing to do: the notice will simply show again next visit.
    }
  };

  return (
    <div className="sandbox-notice" role="dialog" aria-label="About this demo">
      <div className="sandbox-notice__title">You're looking at a sandbox</div>
      <p className="sandbox-notice__body">
        Synthetic freight data, seeded on boot. No emails, SMS or calls leave this
        system. Screens marked <b>Design preview</b> show the intended end state with
        sample data; everything else is computed live from the database.
      </p>
      <button type="button" className="sandbox-notice__button" onClick={dismiss}>
        Got it
      </button>
    </div>
  );
}
