import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { InboxPage } from "@/features/inbox/InboxPage";
import { renderWithProviders } from "@/test/render";

describe("InboxPage", () => {
  it("declares itself a design preview shipping in Increment 3", () => {
    renderWithProviders(<InboxPage />);

    const banner = screen.getByRole("note");
    expect(banner).toHaveTextContent(/design preview/i);
    expect(banner).toHaveTextContent("Increment 3");
  });

  it("draws the hard boundary where the model stops", () => {
    renderWithProviders(<InboxPage />);

    const extraction = screen.getByRole("region", { name: /llm extraction/i });
    expect(
      within(extraction).getByText("The model stops here. Everything below is computed."),
    ).toBeVisible();
    expect(within(extraction).getByText(/"reference": "LD-1048"/)).toBeVisible();
  });

  it("stops a suppressed thread at the failing gate and names the outcome", async () => {
    const user = userEvent.setup();
    renderWithProviders(<InboxPage />);

    await user.click(screen.getByRole("button", { name: /status LD-9999\?/i }));

    const detail = screen.getByRole("region", { name: /thread detail/i });
    expect(within(detail).getByText(/load matched in atlas brokerage/i)).toBeVisible();
    // The dispatcher-language verdict still carries the countable enum as evidence.
    expect(within(detail).getByText(/reference unclear/i)).toBeVisible();
    expect(within(detail).getByText("reference_ambiguous")).toBeVisible();
    // The pipeline halted before a reply: no computed-reply panel is rendered.
    expect(
      within(detail).queryByRole("region", { name: /computed reply/i }),
    ).not.toBeInTheDocument();
  });

  it("suppresses the bounce before the model is ever invoked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<InboxPage />);

    await user.click(
      screen.getByRole("button", { name: /delivery status notification/i }),
    );

    const detail = screen.getByRole("region", { name: /thread detail/i });
    expect(within(detail).getByText("loop_suppressed")).toBeVisible();
    expect(within(detail).getByText(/ten steps not reached/i)).toBeVisible();
    expect(
      within(detail).queryByRole("region", { name: /llm extraction/i }),
    ).not.toBeInTheDocument();
  });
});
