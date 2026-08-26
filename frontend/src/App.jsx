import React, { useState, useEffect, useRef, useCallback } from "react";

const STAGES = [
  { key: "guard_in", label: "GUARDRAIL", sub: "input check" },
  { key: "retrieve", label: "RETRIEVAL", sub: "vector DB" },
  { key: "prompt", label: "PROMPT", sub: "construction" },
  { key: "llm", label: "SYNTHESIS", sub: "claude" },
  { key: "guard_out", label: "GUARDRAIL", sub: "output check" },
];

// Stage timings are a client-side visualization of the pipeline the backend
// actually runs (see app/main.py). The real work happens in one request;
// this sequences the reveal so the trace reads left-to-right as it would
// execute, and snaps to completion the moment the real response lands.
const STAGE_INTERVAL_MS = 420;

function StageTracker({ activeIndex, status }) {
  return (
    <div className="tracker">
      <div className="tracker-node origin" data-state={activeIndex >= 0 ? "done" : "idle"}>
        <span className="node-dot" />
        <span className="node-label">QUERY</span>
      </div>

      {STAGES.map((stage, i) => {
        const state =
          status === "error" && i === activeIndex
            ? "error"
            : i < activeIndex
            ? "done"
            : i === activeIndex
            ? "active"
            : "idle";
        return (
          <React.Fragment key={stage.key}>
            <span className={"tracker-wire " + (i <= activeIndex ? "lit" : "")} />
            <div className="tracker-node" data-state={state}>
              <span className="node-dot" />
              <span className="node-label">{stage.label}</span>
              <span className="node-sub">{stage.sub}</span>
            </div>
          </React.Fragment>
        );
      })}

      <span className={"tracker-wire " + (activeIndex >= STAGES.length ? "lit" : "")} />
      <div className="tracker-node terminus" data-state={activeIndex >= STAGES.length ? "done" : "idle"}>
        <span className="node-dot" />
        <span className="node-label">OUTPUT</span>
      </div>
    </div>
  );
}

function SourceChip({ index, source }) {
  const [expanded, setExpanded] = useState(false);
  const matchPercent = (source.score * 100).toFixed(1);
  return (
    <div className={`source-chip ${expanded ? "expanded" : ""}`} onClick={() => setExpanded(!expanded)}>
      <div className="source-chip-header">
        <span className="source-chip-index">[{index}]</span>
        <span className="source-chip-name">{source.source}</span>
        <span className="source-chip-score">{matchPercent}% Match</span>
      </div>
      {expanded && (
        <div className="source-chip-snippet">
          {source.text}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [chunksStored, setChunksStored] = useState(null);
  const [backendOnline, setBackendOnline] = useState(true);

  const [file, setFile] = useState(null);
  const [ingesting, setIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState("");

  const [queryText, setQueryText] = useState("");
  const [messages, setMessages] = useState([]);
  const [asking, setAsking] = useState(false);
  const [activeStage, setActiveStage] = useState(-1);
  const [stageStatus, setStageStatus] = useState("idle");
  const stageTimer = useRef(null);
  const chatEndRef = useRef(null);

  const refreshStatus = useCallback(async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || "";
      const res = await fetch(`${apiUrl}/status`);
      const data = await res.json();
      setChunksStored(data.chunks_stored);
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleIngest() {
    if (!file) {
      setIngestMsg("Select a .pdf, .txt, or .md file first.");
      return;
    }
    setIngesting(true);
    setIngestMsg("Uploading and indexing…");

    const form = new FormData();
    form.append("file", file);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || "";
      const res = await fetch(`${apiUrl}/ingest`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Ingest failed.");
      setIngestMsg(`Indexed "${data.filename}" — ${data.chunks_added} chunks added.`);
      refreshStatus();
    } catch (e) {
      setIngestMsg("Error: " + e.message);
    } finally {
      setIngesting(false);
    }
  }

  function startStageAnimation() {
    let i = 0;
    setActiveStage(0);
    setStageStatus("running");
    stageTimer.current = setInterval(() => {
      i += 1;
      if (i >= STAGES.length) {
        clearInterval(stageTimer.current);
        return;
      }
      setActiveStage(i);
    }, STAGE_INTERVAL_MS);
  }

  function stopStageAnimation(finalStatus) {
    clearInterval(stageTimer.current);
    setStageStatus(finalStatus);
    setActiveStage(finalStatus === "error" ? activeStage : STAGES.length);
  }

  async function handleAsk() {
    const q = queryText.trim();
    if (!q || asking) return;

    setMessages((m) => [...m, { role: "user", text: q }]);
    setQueryText("");
    setAsking(true);
    startStageAnimation();

    try {
      const apiUrl = import.meta.env.VITE_API_URL || "";
      const res = await fetch(`${apiUrl}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Query failed.");

      stopStageAnimation("done");
      setMessages((m) => [
        ...m,
        { role: "bot", text: data.answer, sources: data.sources },
      ]);
    } catch (e) {
      stopStageAnimation("error");
      setMessages((m) => [...m, { role: "err", text: e.message }]);
    } finally {
      setAsking(false);
      setTimeout(() => {
        setActiveStage(-1);
        setStageStatus("idle");
      }, 900);
    }
  }

  return (
    <div className="sheet">
      <header className="titleblock">
        <div className="titleblock-main">
          <h1>RAG-01</h1>
          <p>RETRIEVAL-AUGMENTED GENERATION — CONSOLE</p>
        </div>
        <div className="titleblock-meta">
          <div>
            <span className="meta-key">STATUS</span>
            <span className={"meta-val " + (backendOnline ? "ok" : "err")}>
              {backendOnline ? "ONLINE" : "UNREACHABLE"}
            </span>
          </div>
          <div>
            <span className="meta-key">INDEXED CHUNKS</span>
            <span className="meta-val">{chunksStored ?? "—"}</span>
          </div>
        </div>
      </header>

      <section className="panel">
        <h2>01 — PIPELINE TRACE</h2>
        <StageTracker activeIndex={activeStage} status={stageStatus} />
      </section>

      <section className="panel">
        <h2>02 — INGEST DOCUMENT</h2>
        <div className="ingest-row">
          <label className="file-input">
            <input
              type="file"
              accept=".pdf,.txt,.md"
              onChange={(e) => setFile(e.target.files[0] || null)}
            />
            <span>{file ? file.name : "Choose file (.pdf / .txt / .md)"}</span>
          </label>
          <button onClick={handleIngest} disabled={ingesting}>
            {ingesting ? (
              <span className="loader-dots">
                INDEXING<span></span><span></span><span></span>
              </span>
            ) : "UPLOAD + INDEX"}
          </button>
        </div>
        {ingestMsg && <p className="hint">{ingestMsg}</p>}
      </section>

      <section className="panel panel-chat">
        <h2>03 — QUERY</h2>
        <div className="chat">
          {messages.length === 0 && (
            <p className="empty">No queries yet. Ask something about an indexed document.</p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={"bubble " + m.role}>
              <p>{m.text}</p>
              {m.sources && m.sources.length > 0 && (
                <div className="sources">
                  {m.sources.map((s, j) => (
                    <SourceChip key={j} index={j + 1} source={s} />
                  ))}
                </div>
              )}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>
        <div className="ask-row">
          <input
            type="text"
            value={queryText}
            placeholder="e.g. What is our paternity leave policy?"
            onChange={(e) => setQueryText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          />
          <button onClick={handleAsk} disabled={asking || !queryText.trim()}>
            {asking ? (
              <span className="loader-dots">
                RUNNING<span></span><span></span><span></span>
              </span>
            ) : "RUN QUERY"}
          </button>
        </div>
      </section>
    </div>
  );
}
