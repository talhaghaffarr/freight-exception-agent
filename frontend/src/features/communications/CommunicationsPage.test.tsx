import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CommunicationsPage } from "@/features/communications/CommunicationsPage";
import { renderWithProviders } from "@/test/render";

describe("CommunicationsPage", () => {
  it("declares itself a design preview shipping in Increment 4", () => {
    renderWithProviders(<CommunicationsPage />);

    const banner = screen.getByRole("note");
    expect(banner).toHaveTextContent(/design preview/i);
    expect(banner).toHaveTextContent("Increment 4");
  });

  it("groups the timeline by day", () => {
    renderWithProviders(<CommunicationsPage />);

    expect(screen.getByRole("heading", { name: "Today" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Yesterday" })).toBeVisible();
  });

  it("records provider uncertainty as delivery unknown and never blindly resends", () => {
    renderWithProviders(<CommunicationsPage />);

    expect(screen.getByText("Delivery unknown")).toBeVisible();
    expect(
      screen.getByText(
        /provider accepted, no receipt — reconciliation pending, no blind resend/,
      ),
    ).toBeVisible();
    // The countable enum rides along as secondary evidence.
    expect(screen.getByText("delivery_unknown")).toBeVisible();
  });

  it("marks the unshipped channels as specified, not broken", () => {
    renderWithProviders(<CommunicationsPage />);

    // One SMS and one voice entry, each carrying the increment note.
    expect(screen.getAllByText("channel ships in Increment 4")).toHaveLength(2);
    const filters = screen
      .getAllByRole("button")
      .filter((button) => button.getAttribute("title") === "Design preview");
    expect(filters.length).toBeGreaterThan(0);
    for (const filter of filters) {
      expect(filter).toBeDisabled();
    }
  });
});
