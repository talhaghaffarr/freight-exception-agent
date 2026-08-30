/**
 * Reactive inbox — design preview for Increment 3.
 *
 * Master–detail over sample threads. The detail column tells the reactive
 * email pipeline top to bottom: captured message, safety gate ladder, the
 * model's one narrow job, then the computed reply. Suppressed threads stop
 * at their failing gate and name the countable outcome.
 */

import { useState } from "react";

import { PreviewBanner } from "@/components/PreviewBanner";
import { SAMPLE_THREADS, type InboxThread } from "./sampleThreads";
import "./Inbox.css";

const GATE_MARK: Record<string, string> = {
  pass: "✓",
  fail: "✕",
  model: "✓",
  skip: "",
};

function ThreadChip({ thread }: { thread: InboxThread }) {
  if (thread.status === "answered") {
    return <span className="ibx-chip ibx-chip--answered">Answered</span>;
  }
  return (
    <span className="ibx-chip ibx-chip--suppressed">
      Suppressed · {thread.outcomeLabel}
    </span>
  );
}

function InboundMessage({ thread }: { thread: InboxThread }) {
  return (
    <section className="ibx-panel" aria-label="Inbound message">
      <header className="ibx-panel__head">
        <h2 className="ibx-panel__title">Inbound message</h2>
        <span className="ibx-panel__note">{thread.messageId} preserved</span>
      </header>
      <div className="ibx-msg">
        <dl className="ibx-msg__meta">
          <div>
            <dt>From</dt>
            <dd>{thread.from}</dd>
          </div>
          <div>
            <dt>To</dt>
            <dd>{thread.to}</dd>
          </div>
          <div>
            <dt>Subject</dt>
            <dd>{thread.subject}</dd>
          </div>
          <div>
            <dt>Received</dt>
            <dd>{thread.received}</dd>
          </div>
        </dl>
        <blockquote className="ibx-quote">{thread.body}</blockquote>
      </div>
    </section>
  );
}

function SafetyGates({ thread }: { thread: InboxThread }) {
  const proceed = thread.status === "answered";
  return (
    <section className="ibx-panel" aria-label="Safety gates">
      <header className="ibx-panel__head">
        <h2 className="ibx-panel__title">Safety gates</h2>
        <span className="ibx-panel__note">{thread.gatesNote}</span>
      </header>
      <ul className="gates">
        {thread.gates.map((gate) => (
          <li key={gate.id} className={`gate gate--${gate.state}`}>
            <span className="gate__mark" aria-hidden="true">
              {GATE_MARK[gate.state]}
            </span>
            <span>
              <span className="gate__label">{gate.label}</span>
              <span className="gate__detail">{gate.detail}</span>
            </span>
          </li>
        ))}
      </ul>
      <p className={`gates__verdict gates__verdict--${proceed ? "proceed" : "held"}`}>
        {proceed ? (
          <>
            <b>Proceed</b> · {thread.verdictNote}
          </>
        ) : (
          <>
            <b>Suppressed</b> · {thread.outcomeLabel} — {thread.verdictNote} · counted
            as <code>{thread.outcome}</code>
          </>
        )}
      </p>
    </section>
  );
}

function Extraction({ thread }: { thread: InboxThread }) {
  const { extraction } = thread;
  if (!extraction) return null;
  return (
    <section className="ibx-panel ibx-panel--model" aria-label="LLM extraction">
      <header className="ibx-panel__head">
        <h2 className="ibx-panel__title">LLM extraction</h2>
        <span className="ibx-chip ibx-chip--model">One narrow job</span>
      </header>
      <div className="extract__body">
        <div>
          <div className="extract__label">What the model saw</div>
          <pre className="extract__block">{extraction.input}</pre>
        </div>
        <p className="extract__note">{extraction.inputNote}</p>
        <div>
          <div className="extract__label">What the model returned</div>
          <pre className="extract__block extract__block--out">{extraction.output}</pre>
        </div>
        <p className="extract__note">{extraction.outputNote}</p>
        <hr className="extract__rule" />
        <p className="extract__stop">The model stops here. Everything below is computed.</p>
      </div>
    </section>
  );
}

function ComputedReply({ thread }: { thread: InboxThread }) {
  const { reply } = thread;
  if (!reply) return null;
  return (
    <section className="ibx-panel" aria-label="Computed reply">
      <header className="ibx-panel__head">
        <h2 className="ibx-panel__title">Computed reply</h2>
        <span className="ibx-panel__note">every number computed, none generated</span>
      </header>
      <div className="reply__body">
        <div className="ibx-facts">
          {reply.facts.map((fact) => (
            <div key={fact.label} className="ibx-fact">
              <div className="ibx-fact__label">{fact.label}</div>
              <div className={`ibx-fact__value${fact.alert ? " ibx-fact__value--alert" : ""}`}>
                {fact.value}
              </div>
              <div className="ibx-fact__note">{fact.note}</div>
            </div>
          ))}
        </div>
        <div className="reply__mail">
          <div className="reply__mailhead">
            <p className="reply__mailsubject">{reply.subject}</p>
            <p className="reply__mailroute">
              from {reply.from} · to {reply.to}
            </p>
          </div>
          <div className="reply__mailbody">
            {reply.paragraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>
          <p className="reply__threading">{reply.threading}</p>
        </div>
      </div>
      <p className="reply__foot">
        <b>Queued</b> · {reply.footer} · <code>{reply.footerEvidence}</code>
      </p>
    </section>
  );
}

export function InboxPage() {
  const [selectedId, setSelectedId] = useState(SAMPLE_THREADS[0]!.id);
  const selected =
    SAMPLE_THREADS.find((thread) => thread.id === selectedId) ?? SAMPLE_THREADS[0]!;

  return (
    <div className="ibx">
      <PreviewBanner increment="Increment 3" />

      <header className="ibx__head">
        <div>
          <h1 className="ibx__title">Reactive inbox</h1>
          <p className="ibx__subtitle">
            Customer status emails — checked at every gate, answered from computed facts.
          </p>
        </div>
      </header>

      <div className="ibx__split">
        <section className="ibx-panel" aria-label="Inbound threads">
          <header className="ibx-panel__head">
            <h2 className="ibx-panel__title">Threads</h2>
            <span className="ibx-panel__note">4 inbound · sample</span>
          </header>
          <ul className="ibx-threads">
            {SAMPLE_THREADS.map((thread) => (
              <li key={thread.id} className="ibx-thread">
                <button
                  type="button"
                  className="ibx-thread__button"
                  aria-current={thread.id === selected.id}
                  onClick={() => setSelectedId(thread.id)}
                >
                  <span className="ibx-thread__top">
                    <span className="ibx-thread__from">{thread.from}</span>
                    <span className="ibx-thread__time">{thread.listTime}</span>
                  </span>
                  <p className="ibx-thread__subject">{thread.subject}</p>
                  <span className="ibx-thread__chiprow">
                    <ThreadChip thread={thread} />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="ibx-detail" aria-label="Thread detail">
          <InboundMessage thread={selected} />
          <SafetyGates thread={selected} />
          <Extraction thread={selected} />
          <ComputedReply thread={selected} />
        </section>
      </div>
    </div>
  );
}
