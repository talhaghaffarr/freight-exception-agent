/**
 * Demo sign-in.
 *
 * There is no password because there is no real identity here: these are seeded
 * demo users, and the API refuses to issue a session at all in live mode.
 */

import { useState, type FormEvent } from "react";

import { ApiError } from "@/app/api";
import { useSession } from "@/app/session";

import "./DemoSignIn.css";

const DEMO_USERS = [
  { email: "operator@relayops.demo", label: "Platform operator", scope: "All tenants" },
  { email: "admin@atlas.demo", label: "Brokerage admin", scope: "Atlas Brokerage" },
  { email: "manager@meridian.demo", label: "Account manager", scope: "Meridian Freight" },
  { email: "reviewer@relayops.demo", label: "Read-only reviewer", scope: "Both tenants" },
];

export function DemoSignIn() {
  const { signIn } = useSession();
  const [email, setEmail] = useState(DEMO_USERS[3]!.email);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await signIn(email);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Sign-in failed. Is the API running?",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="signin">
      <form className="signin__card" onSubmit={onSubmit} aria-labelledby="signin-heading">
        <h1 id="signin-heading" className="signin__title">
          RelayOps
        </h1>
        <p className="signin__lead">
          Demo sign-in. Pick a seeded persona to see what that role is allowed to do.
        </p>

        <fieldset className="signin__personas">
          <legend className="visually-hidden">Demo persona</legend>
          {DEMO_USERS.map((user) => (
            <label key={user.email} className="signin__persona">
              <input
                type="radio"
                name="persona"
                value={user.email}
                checked={email === user.email}
                onChange={(event) => setEmail(event.target.value)}
              />
              <span className="signin__persona-label">{user.label}</span>
              <span className="signin__persona-scope">{user.scope}</span>
            </label>
          ))}
        </fieldset>

        {error && (
          <p className="signin__error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="signin__submit" disabled={pending}>
          {pending ? "Signing in…" : "Enter console"}
        </button>
      </form>
    </main>
  );
}
