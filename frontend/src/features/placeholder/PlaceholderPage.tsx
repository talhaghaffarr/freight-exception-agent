/**
 * A screen a later increment owns.
 *
 * It says which increment fills it in rather than showing an empty panel: an
 * interviewer clicking around should never wonder whether something is broken.
 */

import { Link } from "react-router-dom";

export interface PlaceholderPageProps {
  title: string;
  increment: string;
  description: string;
}

export function PlaceholderPage({ title, increment, description }: PlaceholderPageProps) {
  return (
    <section className="page" aria-labelledby="placeholder-heading">
      <header className="page__header">
        <h1 id="placeholder-heading" className="page__title">
          {title}
        </h1>
      </header>
      <div className="panel panel--empty">
        <p className="panel__lead">{description}</p>
        <p className="panel__meta">Delivered in {increment}.</p>
        <p className="panel__meta">
          <Link to="/system">Check platform health</Link> in the meantime.
        </p>
      </div>
    </section>
  );
}
