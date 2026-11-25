import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import type {
  Config,
  Hand,
  Note,
  Report,
  Review,
  SavedHand,
  Similar,
  Source,
  Stats,
} from "./types";
import "./style.css";

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const result = await fetch("/api" + path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const body = await result.json();
  if (!result.ok) {
    const detail = body.detail;
    throw new Error(
      Array.isArray(detail)
        ? detail
            .map(
              (d: { loc: unknown[]; msg: string }) =>
                `${d.loc.join(".")}: ${d.msg}`,
            )
            .join("\n")
        : detail || "操作失敗",
    );
  }
  return body;
}
const post = (value: unknown): RequestInit => ({
  method: "POST",
  body: JSON.stringify(value),
});
const money = (value: string | number | undefined) =>
  value == null
    ? "—"
    : Number(value).toLocaleString("en-US", { maximumFractionDigits: 2 });
const pct = (value: string | number | null | undefined) =>
  value == null ? "—" : `${(Number(value) * 100).toFixed(2)}%`;
const streets: Record<string, string> = {
  preflop: "翻前",
  flop: "翻牌",
  turn: "轉牌",
  river: "河牌",
};
const actions: Record<string, string> = {
  fold: "棄牌",
  call: "跟注",
  check: "過牌",
  bet: "下注",
  raise: "加注",
};
const paths: Record<string, string> = {
  table: "M3 8h18v8H3z M7 4v4m10-4v4M7 16v4m10-4v4",
  chart: "M4 20V4m0 16h16M8 16v-5m5 5V7m5 9v-8",
  book: "M3 4h7l2 2 2-2h7v15h-7l-2 2-2-2H3zM12 6v15",
  plus: "M12 5v14M5 12h14",
  arrow: "M5 12h14m-5-5 5 5-5 5",
  search: "M16 16l5 5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  close: "M6 6l12 12M6 18 18 6",
  check: "m4 12 5 5L20 6",
  download: "M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4",
  chevron: "m9 5 7 7-7 7",
  spark: "m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3z",
};
function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] || paths.spark} />
    </svg>
  );
}
function Card({ value, small = false }: { value?: string; small?: boolean }) {
  const suit = value?.[1];
  return (
    <span
      className={`card ${small ? "small" : ""} ${suit === "h" || suit === "d" ? "red" : ""} ${!value ? "back" : ""}`}
    >
      {value ? (
        <>
          <b>{value[0]}</b>
          <span>{{ s: "♠", h: "♥", c: "♣", d: "♦" }[suit!]}</span>
        </>
      ) : (
        <span>✦</span>
      )}
    </span>
  );
}

function App() {
  const [page, setPage] = useState<"studio" | "patterns" | "notes">("studio");
  const [config, setConfig] = useState<Config | null>(null),
    [hands, setHands] = useState<SavedHand[]>([]),
    [stats, setStats] = useState<Stats | null>(null),
    [notes, setNotes] = useState<Note[]>([]);
  const [hand, setHand] = useState<Hand | null>(null),
    [report, setReport] = useState<Report | null>(null),
    [review, setReview] = useState<Review | null>(null),
    [savedId, setSavedId] = useState<string | null>(null),
    [similar, setSimilar] = useState<Similar[]>([]);
  const [step, setStep] = useState(9),
    [editor, setEditor] = useState(false),
    [draft, setDraft] = useState(""),
    [text, setText] = useState(""),
    [inputMode, setInputMode] = useState("json"),
    [isDemo, setIsDemo] = useState(true),
    [missing, setMissing] = useState<string[]>([]);
  const [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [filter, setFilter] = useState(""),
    [position, setPosition] = useState(""),
    [query, setQuery] = useState(""),
    [hits, setHits] = useState<Source[] | null>(null),
    [noteForm, setNoteForm] = useState(false),
    [activeSource, setActiveSource] = useState<Source | Note | null>(null);
  const [noteTitle, setNoteTitle] = useState(""),
    [noteBody, setNoteBody] = useState(""),
    [noteTags, setNoteTags] = useState("");
  async function run(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失敗");
    } finally {
      setBusy("");
    }
  }
  async function refresh() {
    const [h, s, n] = await Promise.all([
      api<SavedHand[]>("/hands"),
      api<Stats>("/stats"),
      api<Note[]>("/notes"),
    ]);
    setHands(h);
    setStats(s);
    setNotes(n);
  }
  async function example() {
    const h = await api<Hand>("/example");
    const r = await api<Report>("/analyze", post(h));
    setHand(h);
    setReport(r);
    setDraft(JSON.stringify(h, null, 2));
    setSavedId(null);
    setReview(null);
    setSimilar([]);
    setIsDemo(true);
    setStep(Math.min(9, r.timeline.length - 1));
    setMissing([]);
  }
  useEffect(() => {
    void run("載入工作室", async () => {
      setConfig(await api<Config>("/config"));
      await refresh();
      await example();
    });
  }, []);
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(""), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);
  useEffect(() => {
    if (!editor && !noteForm && !activeSource) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]');
    const elements = () =>
      Array.from(
        dialog?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input, textarea, select, [tabindex="0"]',
        ) || [],
      );
    elements()[0]?.focus();
    const keydown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setEditor(false);
        setNoteForm(false);
        setActiveSource(null);
      }
      if (e.key === "Tab") {
        const items = elements();
        const first = items[0],
          last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      previous?.focus();
    };
  }, [editor, noteForm, activeSource]);
  async function openHand(id: string) {
    const h = await api<SavedHand>("/hands/" + encodeURIComponent(id));
    setHand(h.payload);
    setReport(h.report);
    setDraft(JSON.stringify(h.payload, null, 2));
    setReview(h.review);
    setSavedId(h.id);
    setIsDemo(h.is_demo);
    setStep(Math.max(0, h.report.timeline.length - 1));
    setSimilar(
      await api<Similar[]>("/hands/" + encodeURIComponent(id) + "/similar"),
    );
    setPage("studio");
  }
  async function preview() {
    let h: Hand;
    try {
      h = JSON.parse(draft);
    } catch {
      throw new Error("JSON 格式有誤，請檢查逗號、括號與雙引號。");
    }
    const r = await api<Report>("/analyze", post(h));
    setHand(h);
    setReport(r);
    setReview(null);
    setSavedId(null);
    setSimilar([]);
    setStep(Math.max(0, r.timeline.length - 1));
    setEditor(false);
    setToast("牌譜驗證完成，尚未儲存");
  }
  async function save() {
    if (!hand) return;
    const h = await api<SavedHand>("/hands", post({ hand, is_demo: isDemo }));
    setSavedId(h.id);
    setReview(null);
    await refresh();
    setSimilar(
      await api<Similar[]>("/hands/" + encodeURIComponent(h.id) + "/similar"),
    );
    setToast("牌局已儲存");
  }
  async function makeReview(mode: "rules" | "openai") {
    if (!savedId) return;
    setReview(
      await api<Review>(
        "/hands/" + encodeURIComponent(savedId) + "/review",
        post({ mode }),
      ),
    );
    await refresh();
  }
  function download() {
    if (!hand) return;
    const blob = new Blob([JSON.stringify({ hand, report, review }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${hand.hand_id}-review.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
  const selected = report?.timeline[step];
  const selectedDecision =
    report?.decisions.find((d) => d.index === step) ||
    report?.decisions.find((d) => d.index === step + 1);
  const filtered = hands.filter(
    (h) =>
      (!filter ||
        h.id.toLowerCase().includes(filter.toLowerCase()) ||
        h.report.hero_cards
          .join("")
          .toLowerCase()
          .includes(filter.toLowerCase())) &&
      (!position || h.report.hero_position === position),
  );
  return (
    <div className="app">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("studio");
          }}
        >
          <span className="brand-mark">♠</span>
          <span>
            felt<span className="brand-dot">.</span>
            <small>POKER REVIEW LAB</small>
          </span>
        </a>
        <div className="nav-label">YOUR WORKSPACE</div>
        <nav>
          {(
            [
              ["studio", "table", "牌局工作室"],
              ["patterns", "chart", "決策趨勢"],
              ["notes", "book", "策略知識庫"],
            ] as const
          ).map(([id, icon, label]) => (
            <button
              key={id}
              className={`nav-item ${page === id ? "active" : ""}`}
              onClick={() => setPage(id)}
            >
              <Icon name={icon} />
              {label}
              {page === id && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span>BETTER DECISIONS,</span>
          <strong>one hand at a time.</strong>
          <p>
            留下過程，
            <br />
            讓每一手牌都有收穫。
          </p>
          <div className="mini-cards">
            <Card value="As" small />
            <Card value="Kh" small />
          </div>
        </div>
        <div className="profile">
          <span className="avatar">K</span>
          <div>
            <strong>Koky 的工作室</strong>
            <small>9-MAX · NLH CASH</small>
          </div>
          <span className="online-dot" />
        </div>
      </aside>
      <main>
        <header className="topbar">
          <span>
            工作室 <span className="slash">/</span>{" "}
            {
              {
                studio: "牌局復盤",
                patterns: "個人決策趨勢",
                notes: "策略知識庫",
              }[page]
            }
          </span>
          <span className="status">
            <span className="online-dot" />
            {config?.ai_enabled ? "AI 已設定" : "本機模式"}
            <span className="status-divider" />
            賽後分析
          </span>
        </header>
        <div className="content">
          <div className="page-heading">
            <div className="eyebrow">THE REVIEW ROOM / 01</div>
            <div className="heading-row">
              <div>
                <h1>
                  {
                    {
                      studio: "把一手牌，打得更明白。",
                      patterns: "找到值得再看一眼的決策。",
                      notes: "讓每個觀點，都有出處。",
                    }[page]
                  }
                </h1>
                <p>
                  {
                    {
                      studio: "重播行動、釐清價格，建立自己的決策紀錄。",
                      patterns: "以你記錄的機會為分母，觀察模式，再檢查證據。",
                      notes: "搜尋你的策略筆記，為復盤提供可追溯的參考。",
                    }[page]
                  }
                </p>
              </div>
              <button
                className="button primary"
                disabled={!!busy}
                onClick={() => {
                  setDraft(hand ? JSON.stringify(hand, null, 2) : "");
                  setEditor(true);
                  setInputMode("json");
                  setMissing([]);
                }}
              >
                <Icon name="plus" />
                記錄牌局
              </button>
            </div>
          </div>
          {error && (
            <div className="alert" role="alert">
              <span>{error}</span>
              <button aria-label="關閉錯誤" onClick={() => setError("")}>
                <Icon name="close" />
              </button>
            </div>
          )}
          {busy && (
            <div className="progress" role="status">
              <span className="spinner" />
              {busy}…
            </div>
          )}
          {page === "studio" && (
            <>
              <div className="studio-grid">
                <section className="panel replay-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">HAND REPLAYER</span>
                      <h2>
                        牌桌重播 <span className="tag">9-MAX</span>
                      </h2>
                    </div>
                    <button
                      className="text-button"
                      disabled={!!busy}
                      onClick={() => void run("載入示範", example)}
                    >
                      載入示範 <Icon name="arrow" size={16} />
                    </button>
                  </div>
                  <div className="hand-meta">
                    <span className="mono">
                      {hand ? `$${hand.small_blind} / $${hand.big_blind}` : "—"}
                    </span>
                    <span>NO-LIMIT HOLD’EM</span>
                    <span className="meta-spacer" />
                    <span className={`tag ${isDemo ? "gold" : ""}`}>
                      {isDemo ? "教學示範" : "個人牌局"}
                    </span>
                  </div>
                  <div className="poker-room">
                    <div className="felt">
                      <div className="felt-ring" />
                      <span className="table-watermark">FELT / REVIEW LAB</span>
                      <div className="community">
                        <span className="street-label">
                          {streets[selected?.street || "preflop"]} · POT
                        </span>
                        <strong className="pot">
                          ${money(selected?.pot || "3")}
                        </strong>
                        <div className="board">
                          {Array.from({ length: 5 }, (_, i) => (
                            <Card key={i} value={selected?.board[i]} />
                          ))}
                        </div>
                      </div>
                    </div>
                    {hand?.players.map((p, i) => {
                      const folded = selected?.folded.includes(p.player_id);
                      const hero = p.is_hero;
                      return (
                        <div
                          key={p.player_id}
                          className={`seat seat-${i} ${hero ? "hero" : ""} ${folded ? "folded" : ""} ${selected?.player === p.player_id ? "acting" : ""}`}
                        >
                          <span className="seat-position">
                            {p.position}
                            {hero ? " · YOU" : ""}
                          </span>
                          <div className="seat-stack">
                            <span className="seat-chip">
                              {hero ? "K" : p.seat}
                            </span>
                            <span>
                              $
                              {money(
                                selected?.remaining[p.player_id] ||
                                  p.starting_stack,
                              )}
                            </span>
                          </div>
                          {hero && (
                            <div className="hole-cards">
                              {hand.hero_cards.map((c) => (
                                <Card key={c} value={c} small />
                              ))}
                            </div>
                          )}
                          {selected?.player === p.player_id && (
                            <span className="action-bubble">
                              {actions[selected.action]}
                              {selected.amount_to
                                ? " $" + money(selected.amount_to)
                                : ""}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  <div className="replay-controls">
                    <button
                      className="icon-button"
                      aria-label="上一步"
                      disabled={step <= 0 || !report}
                      onClick={() => setStep(step - 1)}
                    >
                      ‹
                    </button>
                    <input
                      aria-label="重播步驟"
                      type="range"
                      min="0"
                      max={Math.max(0, (report?.timeline.length || 1) - 1)}
                      value={step}
                      onChange={(e) => setStep(Number(e.target.value))}
                    />
                    <button
                      className="icon-button"
                      aria-label="下一步"
                      disabled={!report || step >= report.timeline.length - 1}
                      onClick={() => setStep(step + 1)}
                    >
                      ›
                    </button>
                    <span className="mono step-number">
                      {report?.timeline.length ? step + 1 : 0} /{" "}
                      {report?.timeline.length || 0}
                    </span>
                  </div>
                  <div className="metrics">
                    <div>
                      <span>待跟注價格</span>
                      <strong>{pct(selectedDecision?.call_price)}</strong>
                      <small>行動前快照</small>
                    </div>
                    <div>
                      <span>街初 SPR</span>
                      <strong>
                        {selectedDecision?.street_start_spr
                          ? Number(selectedDecision.street_start_spr).toFixed(2)
                          : "—"}
                      </strong>
                      <small>單挑有效籌碼</small>
                    </div>
                    <div>
                      <span>本次跟注額</span>
                      <strong>${money(selectedDecision?.to_call)}</strong>
                      <small>
                        {selectedDecision
                          ? streets[selectedDecision.street] + " · Hero"
                          : "選擇 Hero 決策"}
                      </small>
                    </div>
                  </div>
                  <div className="panel-footer">
                    <span className="mono truncate">
                      {hand?.hand_id || "尚無牌局"}
                    </span>
                    <button
                      className="text-button"
                      onClick={download}
                      disabled={!hand}
                    >
                      <Icon name="download" size={16} />
                      匯出
                    </button>
                    <button
                      className="button compact"
                      onClick={() => void run("儲存牌局", save)}
                      disabled={!!busy || !hand}
                    >
                      {savedId ? "更新牌局" : "儲存牌局"}
                    </button>
                  </div>
                </section>
                <aside className="review-column">
                  <section className="panel review-panel">
                    <div className="panel-heading">
                      <div>
                        <span className="eyebrow">DECISION NOTES</span>
                        <h2>
                          復盤筆記 <Icon name="spark" size={18} />
                        </h2>
                      </div>
                      <span className="tag">
                        {review?.mode === "openai" ? "AI" : "RULES"}
                      </span>
                    </div>
                    {!savedId && (
                      <div className="save-hint">
                        先儲存牌局，再建立可追溯的復盤紀錄。
                      </div>
                    )}
                    <div className="review-actions">
                      <button
                        className="button"
                        disabled={!savedId || !!busy}
                        onClick={() =>
                          void run("建立規則摘要", () => makeReview("rules"))
                        }
                      >
                        規則摘要
                      </button>
                      <button
                        className="button primary"
                        disabled={!savedId || !!busy || !config?.ai_enabled}
                        onClick={() =>
                          void run("AI 復盤", () => makeReview("openai"))
                        }
                      >
                        <Icon name="spark" size={16} />
                        AI 復盤
                      </button>
                    </div>
                    {!config?.ai_enabled && (
                      <p className="muted small-text">
                        設定後端 .env 的 API Key 可啟用
                        AI；目前重播、搜尋和統計已可使用。
                      </p>
                    )}
                    {review ? (
                      <div className="review-content">
                        <h3>
                          {review.mode === "openai" ? "AI 觀察" : "規則摘要"}
                        </h3>
                        <p>{review.summary}</p>
                        {review.observations.map((o, i) => (
                          <div className="observation" key={i}>
                            <p>{o.text}</p>
                            <div>
                              {o.source_ids.map((id) => (
                                <button
                                  className="citation"
                                  key={id}
                                  onClick={() =>
                                    setActiveSource(
                                      review.sources.find((s) => s.id === id) ||
                                        null,
                                    )
                                  }
                                >
                                  {review.sources.find((s) => s.id === id)
                                    ?.title || id}{" "}
                                  ↗
                                </button>
                              ))}
                            </div>
                          </div>
                        ))}
                        {[
                          ["替代選項", review.alternatives],
                          ["仍缺少的資訊", review.missing_information],
                          ["下次練習", review.next_steps],
                          ["分析假設", review.assumptions],
                        ].map(([title, items]) => (
                          <div key={title as string} className="review-section">
                            <h3>{title as string}</h3>
                            <ul>
                              {(items as string[]).map((s, i) => (
                                <li key={i}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        ))}
                        <div className="review-meta">
                          {review.model || "deterministic rules"} ·{" "}
                          {review.retrieval_backend} · {review.latency_ms} ms
                        </div>
                      </div>
                    ) : (
                      <div className="review-empty">
                        <div className="orb">
                          <Icon name="spark" size={26} />
                        </div>
                        <h3>好決策，從好問題開始。</h3>
                        <p>
                          當時有哪些資訊？
                          <br />
                          你比較過哪些選項？
                          <br />
                          哪些假設還需要驗證？
                        </p>
                        <div className="note-rule" />{" "}
                        <span>重視過程，也保留未知。</span>
                      </div>
                    )}
                  </section>
                  <section className="panel similar-panel">
                    <span className="eyebrow">PAST HANDS</span>
                    <h3>
                      相似的個人牌局{" "}
                      <span>{similar.length.toString().padStart(2, "0")}</span>
                    </h3>
                    {similar.length ? (
                      similar.map((h) => (
                        <button
                          key={h.hand_id}
                          className="similar-item"
                          onClick={() =>
                            void run("開啟牌局", () => openHand(h.hand_id))
                          }
                        >
                          <span>
                            {h.cards.join(" ")} · {h.position}
                            <small>{h.hand_id}</small>
                          </span>
                          <Icon name="chevron" size={16} />
                        </button>
                      ))
                    ) : (
                      <p className="muted small-text">
                        儲存更多相同位置與手牌類型的牌局，逐步累積比較依據。
                      </p>
                    )}
                  </section>
                </aside>
              </div>
              <section className="panel history-panel">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">ACTION HISTORY</span>
                    <h2>行動時間軸</h2>
                  </div>
                  <span className="muted small-text">
                    {report?.complete
                      ? "下注已結束 · 尚未派彩"
                      : `紀錄未完成${report?.next_player ? " · 待 " + report.next_player + " 行動" : ""}`}
                  </span>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>街道</th>
                        <th>玩家</th>
                        <th>動作</th>
                        <th>新增投入</th>
                        <th>動作後底池</th>
                        <th>退回</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report?.timeline.map((s, i) => (
                        <tr
                          key={i}
                          className={i === step ? "selected" : ""}
                          onClick={() => setStep(i)}
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") setStep(i);
                          }}
                        >
                          <td>
                            <span className="street-tag">
                              {streets[s.street]}
                            </span>
                          </td>
                          <td>
                            {
                              hand?.players.find(
                                (p) => p.player_id === s.player,
                              )?.position
                            }{" "}
                            {s.player === report.hero_id && (
                              <span className="you">YOU</span>
                            )}
                          </td>
                          <td>
                            {actions[s.action]}
                            {s.amount_to ? " to $" + money(s.amount_to) : ""}
                          </td>
                          <td className="mono">${money(s.added)}</td>
                          <td className="mono">${money(s.pot)}</td>
                          <td className="mono">
                            {Number(s.refunded) > 0
                              ? "$" + money(s.refunded)
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <section className="panel saved-panel">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">YOUR COLLECTION</span>
                    <h2>
                      已儲存牌局 <span className="count">{hands.length}</span>
                    </h2>
                  </div>
                  <div className="filters">
                    <input
                      aria-label="搜尋已儲存牌局"
                      placeholder="搜尋 ID / 手牌"
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                    />
                    <select
                      aria-label="位置篩選"
                      value={position}
                      onChange={(e) => setPosition(e.target.value)}
                    >
                      <option value="">所有位置</option>
                      {[
                        "UTG",
                        "UTG+1",
                        "UTG+2",
                        "LJ",
                        "HJ",
                        "CO",
                        "BTN",
                        "SB",
                        "BB",
                      ].map((p) => (
                        <option key={p}>{p}</option>
                      ))}
                    </select>
                  </div>
                </div>
                {filtered.length ? (
                  <div className="saved-list">
                    {filtered.map((h) => (
                      <div className="saved-row" key={h.id}>
                        <button
                          onClick={() =>
                            void run("開啟牌局", () => openHand(h.id))
                          }
                        >
                          <span className="saved-cards">
                            {h.report.hero_cards.map((c) => (
                              <Card key={c} value={c} small />
                            ))}
                          </span>
                          <span>
                            <strong>{h.id}</strong>
                            <small>
                              {h.report.hero_position} ·{" "}
                              {h.report.decisions.length} 個決策 ·{" "}
                              {h.is_demo ? "示範" : "個人"}
                            </small>
                          </span>
                          <Icon name="arrow" size={18} />
                        </button>
                        <button
                          className="text-button danger"
                          disabled={!!busy}
                          onClick={() => {
                            if (
                              window.confirm(
                                "刪除這手牌的本機紀錄？可先匯出備份。",
                              )
                            )
                              void run("刪除牌局", async () => {
                                await api(
                                  "/hands/" + encodeURIComponent(h.id),
                                  { method: "DELETE" },
                                );
                                if (savedId === h.id) setSavedId(null);
                                await refresh();
                                setToast("已刪除牌局");
                              });
                          }}
                        >
                          刪除
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    {filter || position
                      ? "沒有符合篩選的牌局。"
                      : "你的第一手復盤，就從今天開始。儲存牌局後會出現在這裡。"}
                  </div>
                )}
              </section>
            </>
          )}
          {page === "patterns" && (
            <>
              <div className="stats-grid">
                {[
                  ["個人牌局", stats?.hands || 0, "不含示範資料"],
                  ["已記錄決策", stats?.decisions || 0, "以已儲存牌譜計算"],
                  ["示範牌局", stats?.demo_hands || 0, "不計入個人模式"],
                ].map(([title, value, sub]) => (
                  <section className="panel stat-card" key={title}>
                    <span>{title}</span>
                    <strong>{value}</strong>
                    <small>{sub}</small>
                  </section>
                ))}
              </div>
              <div className="insight-banner">
                <Icon name="chart" />
                <div>
                  <strong>觀察模式，再驗證假設。</strong>
                  <p>{stats?.limitation}</p>
                </div>
              </div>
              <div className="pattern-grid">
                {stats?.patterns.map((p) => (
                  <section className="panel pattern-card" key={p.id}>
                    <div className="eyebrow">
                      PATTERN / {p.target_action.toUpperCase()}
                    </div>
                    <h2>{p.title}</h2>
                    <div className="pattern-value">
                      {p.rate === null ? "—" : (p.rate * 100).toFixed(0) + "%"}
                      <span>
                        {p.matches} / {p.opportunities} 次機會
                      </span>
                    </div>
                    <div className="bar-track">
                      <div style={{ width: `${(p.rate || 0) * 100}%` }} />
                    </div>
                    <span
                      className={`tag ${p.status === "repeated_pattern" ? "gold" : ""}`}
                    >
                      {p.status === "repeated_pattern"
                        ? "出現重複模式 · 待驗證"
                        : "資料尚不足"}
                    </span>
                    <p>{p.suggestion}</p>
                    <div className="evidence-list">
                      {p.evidence.map((e) => (
                        <button
                          key={e.hand_id + e.decision_index}
                          onClick={() =>
                            void run("查看證據", async () => {
                              await openHand(e.hand_id);
                              setStep(e.decision_index);
                            })
                          }
                        >
                          {e.hand_id}{" "}
                          <span>決策 {e.decision_index + 1} ↗</span>
                        </button>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            </>
          )}
          {page === "notes" && (
            <>
              <div className="knowledge-tools">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void run("搜尋筆記", async () =>
                      setHits(
                        (
                          await api<{ hits: Source[] }>(
                            "/search?q=" + encodeURIComponent(query),
                          )
                        ).hits,
                      ),
                    );
                  }}
                >
                  <Icon name="search" />
                  <input
                    aria-label="搜尋策略筆記"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="試試 pot odds、低 SPR 或超大 open…"
                    required
                  />
                  <button className="button primary" disabled={!!busy}>
                    搜尋
                  </button>
                </form>
                <button className="button" onClick={() => setNoteForm(true)}>
                  <Icon name="plus" size={17} />
                  新增筆記
                </button>
              </div>
              <div className="knowledge-caption">
                {hits !== null
                  ? `檢索結果 ${hits.length} 筆`
                  : `${notes.length} 份筆記`}{" "}
                ·{" "}
                {config?.retrieval === "openai"
                  ? "Embedding 語意檢索"
                  : "BM25 關鍵字檢索"}
                {hits !== null && (
                  <button
                    className="text-button"
                    onClick={() => {
                      setHits(null);
                      setQuery("");
                    }}
                  >
                    顯示全部
                  </button>
                )}
              </div>
              <div className="notes-grid">
                {(hits === null ? notes : hits).map((n) => (
                  <button
                    key={n.id}
                    className="panel note-card"
                    onClick={() => setActiveSource(n)}
                  >
                    <span className="note-icon">
                      <Icon name="book" />
                    </span>
                    <h2>{n.title}</h2>
                    <p>{n.body}</p>
                    <div>
                      {n.tags.map((tag) => (
                        <span className="tag" key={tag}>
                          {tag}
                        </span>
                      ))}
                    </div>
                    <footer>
                      {n.source}
                      <Icon name="arrow" size={17} />
                    </footer>
                  </button>
                ))}
              </div>
              {hits?.length === 0 && (
                <div className="empty-state">
                  沒有找到相關筆記，試著換個詞或新增自己的筆記。
                </div>
              )}
            </>
          )}
          <footer className="app-footer">
            <span>FELT / REVIEW LAB</span>
            <span>以事實重播，以證據復盤。</span>
            <span>v1.0 · LOCAL FIRST</span>
          </footer>
        </div>
      </main>
      {toast && (
        <div className="toast" role="status">
          <Icon name="check" />
          {toast}
        </div>
      )}
      {editor && (
        <div className="modal-backdrop">
          <section
            className="modal editor-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="editor-title"
          >
            <div className="modal-heading">
              <div>
                <span className="eyebrow">CAPTURE A HAND</span>
                <h2 id="editor-title">記錄一手牌局</h2>
              </div>
              <button
                className="icon-button"
                aria-label="關閉牌局編輯器"
                onClick={() => setEditor(false)}
              >
                <Icon name="close" />
              </button>
            </div>
            <div className="tabs">
              <button
                className={inputMode === "json" ? "active" : ""}
                onClick={() => setInputMode("json")}
              >
                JSON 牌譜
              </button>
              <button
                className={inputMode === "text" ? "active" : ""}
                onClick={() => setInputMode("text")}
              >
                文字轉換 <span>AI</span>
              </button>
            </div>
            {inputMode === "json" ? (
              <>
                <p className="muted small-text">
                  完整保留 9 位玩家、盲注和動作。amount_to
                  表示本街總投入；未知資訊請先確認。
                </p>
                <textarea
                  className="json-editor"
                  aria-label="JSON 牌譜"
                  spellCheck={false}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                />
              </>
            ) : (
              <>
                <p className="muted small-text">
                  輸入賽後筆記。AI 會產生待確認草稿，缺少資訊不會自動補齊。
                </p>
                <textarea
                  className="text-editor"
                  aria-label="文字牌局筆記"
                  placeholder="例如：1/2、9 人桌，BTN QQ…"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
                <button
                  className="button"
                  disabled={!!busy || !text || !config?.ai_enabled}
                  onClick={() =>
                    void run("轉換牌譜草稿", async () => {
                      const result = await api<{
                        draft_json: string;
                        missing_information: string[];
                      }>("/parse", post({ text }));
                      setDraft(
                        JSON.stringify(JSON.parse(result.draft_json), null, 2),
                      );
                      setMissing(result.missing_information);
                      setInputMode("json");
                    })
                  }
                >
                  轉換為 JSON 草稿
                </button>
                {!config?.ai_enabled && (
                  <p className="muted">設定後端 API Key 後可使用文字轉換。</p>
                )}
              </>
            )}
            {missing.length > 0 && (
              <div className="missing-info">
                <strong>仍需確認</strong>
                <ul>
                  {missing.map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="modal-footer">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={isDemo}
                  onChange={(e) => setIsDemo(e.target.checked)}
                />
                這是示範資料，不計入個人統計
              </label>
              <button
                className="button primary"
                disabled={!!busy || inputMode !== "json"}
                onClick={() => void run("驗證並重播", preview)}
              >
                驗證並重播 <Icon name="arrow" size={17} />
              </button>
            </div>
            {error && (
              <p className="inline-error" role="alert">
                {error}
              </p>
            )}
          </section>
        </div>
      )}
      {activeSource && (
        <div className="modal-backdrop" onClick={() => setActiveSource(null)}>
          <section
            className="modal source-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="source-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-heading">
              <div>
                <span className="eyebrow">SOURCE / REFERENCE</span>
                <h2 id="source-title">{activeSource.title}</h2>
              </div>
              <button
                className="icon-button"
                aria-label="關閉來源"
                onClick={() => setActiveSource(null)}
              >
                <Icon name="close" />
              </button>
            </div>
            <span className="muted small-text">{activeSource.source}</span>
            <p className="source-body">{activeSource.body}</p>
            <div className="source-id mono">{activeSource.id}</div>
          </section>
        </div>
      )}
      {noteForm && (
        <div className="modal-backdrop">
          <form
            className="modal source-modal"
            onSubmit={(e) => {
              e.preventDefault();
              void run("儲存筆記", async () => {
                await api(
                  "/notes",
                  post({
                    title: noteTitle,
                    body: noteBody,
                    tags: noteTags
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  }),
                );
                await refresh();
                setNoteForm(false);
                setNoteTitle("");
                setNoteBody("");
                setNoteTags("");
                setHits(null);
                setToast("策略筆記已儲存");
              });
            }}
          >
            <div className="modal-heading">
              <h2>新增策略筆記</h2>
              <button
                type="button"
                className="icon-button"
                aria-label="關閉筆記表單"
                onClick={() => setNoteForm(false)}
              >
                <Icon name="close" />
              </button>
            </div>
            <label className="field-label">
              標題
              <input
                required
                maxLength={200}
                value={noteTitle}
                onChange={(e) => setNoteTitle(e.target.value)}
              />
            </label>
            <label className="field-label">
              內容與適用條件
              <textarea
                required
                rows={8}
                maxLength={20000}
                value={noteBody}
                onChange={(e) => setNoteBody(e.target.value)}
              />
            </label>
            <label className="field-label">
              標籤（逗號分隔）
              <input
                value={noteTags}
                onChange={(e) => setNoteTags(e.target.value)}
              />
            </label>
            <button className="button primary" disabled={!!busy}>
              儲存筆記
            </button>
            {error && (
              <p role="alert" className="inline-error">
                {error}
              </p>
            )}
          </form>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
