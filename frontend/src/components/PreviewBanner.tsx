/**
 * Marks a screen whose content is a design preview rather than live product.
 *
 * Honesty is the product's selling point, so the banner never hides: it names
 * the increment that ships the real thing and says the data below is sample.
 */

import "./PreviewBanner.css";

export function PreviewBanner({ increment }: { increment: string }) {
  return (
    <div className="preview-banner" role="note">
      <span className="preview-banner__chip">Design preview</span>
      <span>
        Sample data — this surface ships in <b>{increment}</b>. Layout and copy show the
        intended end state.
      </span>
    </div>
  );
}
