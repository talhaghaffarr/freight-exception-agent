/**
 * Sample threads for the Reactive Inbox design preview.
 *
 * Four inbound emails, one per failure mode the gate ladder exists for. The
 * gate rows follow the PRD §10.2 order — loop and rate checks run before
 * sender verification, and the extractor is only ever reached at step 8.
 *
 * Copy rule: primary labels speak dispatcher; the countable outcome enums
 * (PRD §8.5) ride along as secondary mono evidence, never alone.
 */

export type GateState = "pass" | "fail" | "model" | "skip";

export interface GateRow {
  id: string;
  label: string;
  detail: string;
  state: GateState;
}

export interface ReplyFact {
  label: string;
  value: string;
  note: string;
  alert?: boolean;
}

export interface InboxThread {
  id: string;
  from: string;
  to: string;
  subject: string;
  received: string;
  listTime: string;
  messageId: string;
  body: string;
  status: "answered" | "suppressed";
  /** Countable outcome name from PRD §8.5; null while the goal succeeded. */
  outcome: string | null;
  /** Dispatcher-language rendering of the outcome. */
  outcomeLabel: string | null;
  gatesNote: string;
  verdictNote: string;
  gates: GateRow[];
  extraction?: {
    input: string;
    inputNote: string;
    output: string;
    outputNote: string;
  };
  reply?: {
    facts: ReplyFact[];
    subject: string;
    from: string;
    to: string;
    paragraphs: string[];
    threading: string;
    footer: string;
    footerEvidence: string;
  };
}

export const SAMPLE_THREADS: InboxThread[] = [
  {
    id: "thread-ld-1048",
    from: "dana@acmeretail.example",
    to: "status@atlasbrokerage.demo",
    subject: "Where is LD-1048?",
    received: "Sun Aug 31 · 08:47:12 CDT",
    listTime: "08:47",
    messageId: "<9f2c41b8.dana@acmeretail.example>",
    body: "Morning — where is LD-1048 right now? Does the 10:00 pickup still hold?\n\nDana",
    status: "answered",
    outcome: null,
    outcomeLabel: null,
    gatesNote: "steps 2–6 of 12 · order enforced",
    verdictNote: "cleaned message handed to the model",
    gates: [
      {
        id: "loop",
        label: "Not an auto-reply",
        detail: "no Auto-Submitted header · not a bounce · not a provider probe",
        state: "pass",
      },
      {
        id: "rate",
        label: "Within send limits",
        detail: "sender 1/10 per hour · tenant 4/200",
        state: "pass",
      },
      {
        id: "envelope",
        label: "Sender address verified",
        detail: "envelope from dana@acmeretail.example · known contact on LD-1048",
        state: "pass",
      },
      {
        id: "signature",
        label: "Genuine provider message",
        detail: "provider signature valid · webhook HMAC verified",
        state: "pass",
      },
      {
        id: "spf",
        label: "Not spoofed",
        detail: "spf=pass · dkim=pass · dmarc=pass",
        state: "pass",
      },
      {
        id: "enrolled",
        label: "Sender enrolled for status updates",
        detail: "tenant resolved: Atlas Brokerage (exactly one)",
        state: "pass",
      },
    ],
    extraction: {
      input:
        "Morning — where is LD-1048 right now? Does the 10:00 pickup still hold?",
      inputNote: "quote history and HTML stripped · original kept for audit",
      output: `{
  "reference": "LD-1048",
  "intent": "eta",
  "confidence": 0.97
}`,
      outputNote: "a load reference and a question type — never a fact about the load",
    },
    reply: {
      facts: [
        { label: "Position", value: "Springfield, MO", note: "GPS 4 min old" },
        { label: "Appointment", value: "10:00 AM", note: "rev 3" },
        { label: "Computed ETA", value: "10:38 AM", note: "route estimate" },
        { label: "Status", value: "Late +38 min", note: "threshold 30 min", alert: true },
      ],
      subject: "Re: Where is LD-1048?",
      from: "status@atlasbrokerage.demo",
      to: "dana@acmeretail.example",
      paragraphs: [
        "Hi Dana,",
        "LD-1048 is near Springfield, MO as of 08:43 CDT. Pickup is scheduled for 10:00 AM; the computed ETA is 10:38 AM — about 38 minutes behind the appointment.",
        "We will follow up if that changes. Your account manager is dana.reyes@atlasbrokerage.demo.",
        "— Atlas Brokerage operations",
      ],
      threading: "lands in Dana's existing thread · In-Reply-To preserved",
      footer: "one reply, sent exactly once",
      footerEvidence: "idempotent action · provider id pending",
    },
  },
  {
    id: "thread-ld-9999",
    from: "ops@customer.example",
    to: "status@atlasbrokerage.demo",
    subject: "status LD-9999?",
    received: "Sun Aug 31 · 08:12:40 CDT",
    listTime: "08:12",
    messageId: "<74ab02e1.ops@customer.example>",
    body: "Can you send status on LD-9999? Need it for the morning call.\n\n— Ops desk",
    status: "suppressed",
    outcome: "reference_ambiguous",
    outcomeLabel: "Reference unclear",
    gatesNote: "stopped at step 9 of 12",
    verdictNote: "two loads could match; the agent does not guess",
    gates: [
      {
        id: "loop",
        label: "Not an auto-reply",
        detail: "no auto-reply markers",
        state: "pass",
      },
      {
        id: "rate",
        label: "Within send limits",
        detail: "sender 2/10 per hour · tenant 4/200",
        state: "pass",
      },
      {
        id: "envelope",
        label: "Sender address verified",
        detail: "envelope from ops@customer.example · known contact",
        state: "pass",
      },
      {
        id: "signature",
        label: "Genuine provider message",
        detail: "provider signature valid · webhook HMAC verified",
        state: "pass",
      },
      {
        id: "spf",
        label: "Not spoofed",
        detail: "spf=pass · dkim=pass",
        state: "pass",
      },
      {
        id: "enrolled",
        label: "Sender enrolled for status updates",
        detail: "tenant resolved: Atlas Brokerage (exactly one)",
        state: "pass",
      },
      {
        id: "extract",
        label: "Model read the request",
        detail: '{"reference": "LD-9999", "intent": "eta", "confidence": 0.91}',
        state: "model",
      },
      {
        id: "resolve",
        label: "Load matched in Atlas Brokerage",
        detail: "LD-9999 · 0 exact matches · 2 near: LD-9990, LD-9909",
        state: "fail",
      },
    ],
  },
  {
    id: "thread-marketing",
    from: "unknown@fw-marketing.example",
    to: "status@atlasbrokerage.demo",
    subject: "Re: pickup today",
    received: "Sun Aug 31 · 07:56:03 CDT",
    listTime: "07:56",
    messageId: "<blast-2210.unknown@fw-marketing.example>",
    body: "Quick heads up on your pickup program — we move loads in your lanes at 12% under market. Reply STOP to opt out.",
    status: "suppressed",
    outcome: "sender_unverified",
    outcomeLabel: "Sender not verified",
    gatesNote: "stopped at step 4 of 12",
    verdictNote: "address not on file for any customer",
    gates: [
      {
        id: "loop",
        label: "Not an auto-reply",
        detail: "no auto-reply markers",
        state: "pass",
      },
      {
        id: "rate",
        label: "Within send limits",
        detail: "sender 1/10 per hour",
        state: "pass",
      },
      {
        id: "envelope",
        label: "Sender address verified",
        detail: "unknown@fw-marketing.example · not on file · spf=softfail",
        state: "fail",
      },
      {
        id: "not-reached",
        label: "Nine steps not reached",
        detail: "the model never saw this message",
        state: "skip",
      },
    ],
  },
  {
    id: "thread-bounce",
    from: "mailer-daemon@mx.customer.example",
    to: "status@atlasbrokerage.demo",
    subject: "Delivery Status Notification (Failure)",
    received: "Sun Aug 31 · 07:41:29 CDT",
    listTime: "07:41",
    messageId: "<dsn-88041.mailer-daemon@mx.customer.example>",
    body: "This is an automatically generated Delivery Status Notification.\n\nDelivery to the following recipient failed permanently:\nops@customer.example",
    status: "suppressed",
    outcome: "loop_suppressed",
    outcomeLabel: "Auto-reply loop",
    gatesNote: "stopped at step 2 of 12",
    verdictNote: "never answer a bounce",
    gates: [
      {
        id: "loop",
        label: "Not an auto-reply",
        detail: "Auto-Submitted: auto-replied · Precedence: bounce",
        state: "fail",
      },
      {
        id: "not-reached",
        label: "Ten steps not reached",
        detail: "the model never saw this message",
        state: "skip",
      },
    ],
  },
];
