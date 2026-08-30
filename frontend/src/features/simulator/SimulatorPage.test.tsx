import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { RaceResult } from "@/app/types";
import { SimulatorPage } from "@/features/simulator/SimulatorPage";
import { renderWithProviders } from "@/test/render";

const RACE: RaceResult = {
  reference: "LD-1048",
  trigger_fingerprint: "late_pickup:LD-1048:rev3",
  goals_created: 1,
  opened_events: 1,
  duplicates_prevented: 1,
  constraint: "goals_idempotency_key",
  attempts: [
    {
      worker: "scanner-a",
      created: true,
      outcome: "inserted",
      goal_id: "aaaaaaaa-1111-5111-8111-111111111111",
      duration_ms: 12.4,
    },
    {
      worker: "scanner-b",
      created: false,
      outcome: "unique_conflict",
      goal_id: "aaaaaaaa-1111-5111-8111-111111111111",
      duration_ms: 13.1,
    },
  ],
};

describe("SimulatorPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("races two scanners through the real endpoint and shows what Postgres decided", async () => {
    const spy = vi.spyOn(api, "raceScanners").mockResolvedValue(RACE);
    const user = userEvent.setup();
    renderWithProviders(<SimulatorPage />);

    await user.click(screen.getByRole("button", { name: /race two scanners/i }));

    await waitFor(() => expect(spy).toHaveBeenCalledWith("atlas-brokerage", "LD-1048"));
    const card = await screen.findByRole("region", { name: /racing scanners/i });
    expect(within(card).getByText("UNIQUE CONFLICT")).toBeVisible();

    const duplicates = within(card)
      .getByText("Duplicates prevented")
      .closest(".sim-fact") as HTMLElement;
    expect(within(duplicates).getByText("1")).toBeVisible();
  });

  it("resets the demo and reports the counts", async () => {
    const spy = vi
      .spyOn(api, "resetDemo")
      .mockResolvedValue({ goals_cleared: 12, loads_reseeded: 48 });
    const user = userEvent.setup();
    renderWithProviders(<SimulatorPage />);

    await user.click(screen.getByRole("button", { name: /reset demo/i }));

    await waitFor(() => expect(spy).toHaveBeenCalledWith("atlas-brokerage"));
    const card = screen.getByRole("region", { name: /reset demo/i });
    expect(await within(card).findByText("Goals cleared")).toBeVisible();
    expect(within(card).getByText("12")).toBeVisible();
    expect(within(card).getByText("48")).toBeVisible();
  });

  it("keeps the specified scenarios visibly disabled", () => {
    renderWithProviders(<SimulatorPage />);

    const buttons = screen.getAllByRole("button", { name: /run scenario/i });
    expect(buttons).toHaveLength(3);
    for (const button of buttons) {
      expect(button).toBeDisabled();
    }
    expect(screen.getAllByText("Specified")).toHaveLength(3);
  });
});
