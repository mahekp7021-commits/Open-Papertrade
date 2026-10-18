"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, RefreshCw, ShieldCheck, Wallet } from "lucide-react";
import Sidebar from "@/components/Sidebar";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
type Account = { id: number; name: string; username: string; role: string; enabled: boolean; demoBalance: string; leverage: number; spreadPips: string; marginCallLevelPercent: string; stopOutLevelPercent: string; maxPositionSize: string };
type Position = { id: number; symbol: string; side: string; lots: string; entryPrice: string; entryMidPrice: string; spreadPips: string; marginUsed: string; leverage: number; status: string; realizedPnl: string; openReason: string; closeReason: string; openedAt: string; closedAt: string | null };
type Snapshot = { balance: string; unrealizedPnl: string; equity: string; usedMargin: string; freeMargin: string; marginLevelPercent: string | null; riskStatus: string; positions: Array<{ id: number; symbol: string; side: string; lots: string; entryPrice: string; midPrice: string | null; estimatedExitPrice: string | null; unrealizedPnl: string | null; marginUsed: string; leverageAtOpen: number; openedAt: string }> };
type BoardCard = { id: number; accountId: number; symbol: string; side: "BUY" | "SELL"; entryPrice: string; marginAmount: string; leverage: number; lots: string; status: string; tradeTime: string; lessonTitle: string; explanation: string; createdAt: string; updatedAt: string };
type EventRow = { id: number; eventType: string; symbol: string; side: string; lots: string; price: string; pnl: string; marginUsed: string; reason: string; actor: string | null; createdAt: string };

async function api(path: string, method = "GET", body?: unknown) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: "include",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || data.detail || `Request failed (${response.status})`);
  return data;
}
const money = (value?: string | null) => value == null ? "—" : Number(value).toLocaleString("en-US", { style: "currency", currency: "USD" });
const panel = "rounded-2xl border border-[var(--border-muted)] bg-[var(--bg-card)] p-5";
const field = "w-full rounded-xl border border-[var(--border-muted)] bg-[var(--bg-card-inner)] px-3 py-2.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-primary)]";
const label = "mb-1.5 block text-xs font-medium text-[var(--text-secondary)]";

export default function ForexTrainingPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState("");
  const [positions, setPositions] = useState<Position[]>([]);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [boardCards, setBoardCards] = useState<BoardCard[]>([]);
  const [editingCardId, setEditingCardId] = useState<number | null>(null);
  const [boardSymbol, setBoardSymbol] = useState("USDJPY");
  const [boardSide, setBoardSide] = useState<"BUY" | "SELL">("BUY");
  const [boardPrice, setBoardPrice] = useState("150.25000");
  const [boardMargin, setBoardMargin] = useState("500.00");
  const [boardLeverage, setBoardLeverage] = useState("100");
  const [boardLots, setBoardLots] = useState("0.10");
  const [boardStatus, setBoardStatus] = useState("EXAMPLE");
  const [boardTime, setBoardTime] = useState(new Date().toISOString().slice(0,16));
  const [boardTitle, setBoardTitle] = useState("Entry and risk lesson");
  const [boardExplanation, setBoardExplanation] = useState("");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [symbol, setSymbol] = useState("EURUSD");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [lots, setLots] = useState("0.10");
  const [midPrice, setMidPrice] = useState("1.08500");
  const [quotesText, setQuotesText] = useState('{"EURUSD":"1.08500","GBPUSD":"1.27000","AUDUSD":"0.66000","NZDUSD":"0.61000"}');
  const [quoteSource, setQuoteSource] = useState("Manual demo prices");
  const [quoteUpdatedAt, setQuoteUpdatedAt] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [reason, setReason] = useState("Practice trade for training review");
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const selected = accounts.find((account) => String(account.id) === accountId);

  const loadAccounts = useCallback(async () => {
    const data = await api("/users/training/accounts/");
    const rows = data.accounts || [];
    setAccounts(rows);
    setAccountId((current: string) => current && rows.some((row: Account) => String(row.id) === current) ? current : rows[0] ? String(rows[0].id) : "");
  }, []);

  const loadBoard = useCallback(async (id: string) => {
    if (!id) { setBoardCards([]); return; }
    const data = await api(`/users/training/accounts/${id}/teaching-board/`);
    setBoardCards(data.cards || []);
  }, []);

  const loadHistory = useCallback(async (id: string) => {
    if (!id) return;
    const data = await api(`/users/training/accounts/${id}/forex/positions/`);
    setPositions(data.positions || []);
    setEvents(data.events || []);
  }, []);

  useEffect(() => {
    loadAccounts().catch((error) => setMessage({ kind: "error", text: error.message })).finally(() => setLoading(false));
  }, [loadAccounts]);

  useEffect(() => {
    if (accountId) {
      loadHistory(accountId).catch((error) => setMessage({ kind: "error", text: error.message }));
      loadBoard(accountId).catch((error) => setMessage({ kind: "error", text: error.message }));
    }
    setSnapshot(null);
  }, [accountId, loadHistory, loadBoard]);

  const runAction = async (action: () => Promise<void>) => {
    setBusy(true); setMessage(null);
    try { await action(); }
    catch (error) { setMessage({ kind: "error", text: error instanceof Error ? error.message : "Something went wrong." }); }
    finally { setBusy(false); }
  };

  const parseQuotes = () => {
    const value = JSON.parse(quotesText);
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error('Quotes must be a JSON object, e.g. {"EURUSD":"1.08500"}.');
    return value as Record<string, string>;
  };

  const loadReferenceRates = () => runAction(async () => {
    // Daily reference data only; these are not streaming or broker quotes.
    const response = await fetch("https://open.er-api.com/v6/latest/USD", { cache: "no-store" });
    if (!response.ok) throw new Error("Reference-rate service is unavailable. You can still enter demo prices manually.");
    const data = await response.json();
    if (data.result !== "success" || !data.rates) throw new Error("Reference-rate service returned invalid data.");
    const pairs = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"];
    const quotes: Record<string, string> = {};
    for (const pair of pairs) {
      const quotePerUsd = Number(data.rates[pair.slice(3)]);
      if (Number.isFinite(quotePerUsd) && quotePerUsd > 0) quotes[pair] = (1 / quotePerUsd).toFixed(5);
    }
    if (!Object.keys(quotes).length) throw new Error("No supported reference rates were returned.");
    setQuotesText(JSON.stringify(quotes, null, 2));
    if (quotes[symbol]) setMidPrice(quotes[symbol]);
    setQuoteSource("Daily public reference rates (not live market quotes)");
    setQuoteUpdatedAt(data.time_last_update_utc || new Date().toISOString());
    setMessage({ kind: "ok", text: "Reference rates loaded. These are indicative daily rates, not streaming FX prices." });
  });

  useEffect(() => {
    if (!autoRefresh || !accountId) return;
    const timer = window.setInterval(async () => {
      try {
        const quotes = parseQuotes();
        const data = await api("/users/training/accounts/" + accountId + "/forex/snapshot/", "POST", { quotes });
        setSnapshot(data);
        await loadHistory(accountId);
      } catch { /* Keep the last successful valuation visible. */ }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, accountId, quotesText, loadHistory]);

  const refreshSnapshot = () => runAction(async () => {
    if (!accountId) throw new Error("Select a training account first.");
    const data = await api(`/users/training/accounts/${accountId}/forex/snapshot/`, "POST", { quotes: parseQuotes() });
    setSnapshot(data);
    await loadHistory(accountId);
    setMessage({ kind: "ok", text: "Demo valuation refreshed using the supplied prices." });
  });

  const openPosition = () => runAction(async () => {
    if (!accountId) throw new Error("Select a training account first.");
    const quotes = parseQuotes();
    quotes[symbol] = midPrice;
    const data = await api(`/users/training/accounts/${accountId}/forex/open/`, "POST", { symbol, side, lots, midPrice, quotes, reason });
    setMessage({ kind: "ok", text: `Demo ${side} opened: ${lots} lot(s) ${symbol}. No live order was sent.` });
    await loadHistory(accountId);
    const valuation = await api(`/users/training/accounts/${accountId}/forex/snapshot/`, "POST", { quotes });
    setSnapshot(valuation);
  });


  const resetBoardForm = () => { setEditingCardId(null); setBoardSymbol("USDJPY"); setBoardSide("BUY"); setBoardPrice("150.25000"); setBoardMargin("500.00"); setBoardLeverage("100"); setBoardLots("0.10"); setBoardStatus("EXAMPLE"); setBoardTime(new Date().toISOString().slice(0,16)); setBoardTitle("Entry and risk lesson"); setBoardExplanation(""); };

  const saveBoardCard = () => runAction(async () => {
    if (!accountId) throw new Error("Select a training account first.");
    const payload = { symbol: boardSymbol, side: boardSide, entryPrice: boardPrice, marginAmount: boardMargin, leverage: boardLeverage, lots: boardLots, status: boardStatus, tradeTime: new Date(boardTime).toISOString(), lessonTitle: boardTitle, explanation: boardExplanation };
    const path = editingCardId ? `/users/training/accounts/${accountId}/teaching-board/${editingCardId}/` : `/users/training/accounts/${accountId}/teaching-board/`;
    await api(path, editingCardId ? "PATCH" : "POST", payload);
    await loadBoard(accountId);
    setMessage({ kind: "ok", text: editingCardId ? "Teaching card updated. Wallet and actual trade ledger were not changed." : "Teaching card created. This is a classroom example, not an executed trade." });
    resetBoardForm();
  });

  const editBoardCard = (card: BoardCard) => {
    setEditingCardId(card.id); setBoardSymbol(card.symbol); setBoardSide(card.side); setBoardPrice(card.entryPrice);
    setBoardMargin(card.marginAmount); setBoardLeverage(String(card.leverage)); setBoardLots(card.lots); setBoardStatus(card.status);
    setBoardTime(new Date(card.tradeTime).toISOString().slice(0,16)); setBoardTitle(card.lessonTitle); setBoardExplanation(card.explanation);
  };

  const deleteBoardCard = (card: BoardCard) => runAction(async () => {
    await api(`/users/training/accounts/${accountId}/teaching-board/${card.id}/`, "DELETE");
    await loadBoard(accountId);
    if (editingCardId === card.id) resetBoardForm();
    setMessage({ kind: "ok", text: "Teaching card removed. Actual Forex history and wallet were untouched." });
  });

  const editForexPosition = (position: Position) => runAction(async () => {
    const symbolValue = window.prompt("Symbol (USD-quoted FX pair, e.g. EURUSD)", position.symbol);
    if (symbolValue === null) return;
    const sideValue = window.prompt("Side: BUY or SELL", position.side);
    if (sideValue === null) return;
    const lotsValue = window.prompt("Lots", position.lots);
    if (lotsValue === null) return;
    const entryMidValue = window.prompt("Entry mid-price (before spread)", position.entryMidPrice || position.entryPrice);
    if (entryMidValue === null) return;
    const leverageValue = window.prompt("Leverage at open (number only, e.g. 400)", String(position.leverage));
    if (leverageValue === null) return;
    const openedValue = window.prompt("Opened at (ISO date/time)", position.openedAt);
    if (openedValue === null) return;
    let closeMidPrice: string | undefined;
    let closedAt: string | undefined;
    if (position.status === "CLOSED") {
      const closeValue = window.prompt("Corrected close mid-price (leave blank to keep existing close price)", "");
      if (closeValue === null) return;
      if (closeValue.trim()) closeMidPrice = closeValue.trim();
      const closeTimeValue = window.prompt("Closed at (ISO date/time)", position.closedAt || "");
      if (closeTimeValue === null) return;
      if (closeTimeValue.trim()) closedAt = closeTimeValue.trim();
    }
    const correctionReason = window.prompt("Reason for correction (required for audit)", "Trainer correction for lesson accuracy");
    if (!correctionReason?.trim()) throw new Error("A correction reason is required.");
    const payload: Record<string, string> = {
      symbol: symbolValue.trim().toUpperCase(), side: sideValue.trim().toUpperCase(),
      lots: lotsValue.trim(), entryMidPrice: entryMidValue.trim(),
      leverageAtOpen: leverageValue.trim(), openedAt: openedValue.trim(), reason: correctionReason.trim()
    };
    if (closeMidPrice) payload.closeMidPrice = closeMidPrice;
    if (closedAt) payload.closedAt = closedAt;
    const result = await api(`/users/training/accounts/${accountId}/forex/positions/${position.id}/edit/`, "PATCH", payload);
    await loadHistory(accountId);
    setSnapshot(null);
    setMessage({ kind: "ok", text: `Trade corrected. Recalculated P/L: ${money(result.realizedPnl)} · Virtual wallet: ${money(result.walletBalance)}. Previous events remain in history.` });
  });

  const closePosition = (position: Position) => runAction(async () => {
    const quotes = parseQuotes();
    const price = quotes[position.symbol] || (position.symbol === symbol ? midPrice : "");
    if (!price) throw new Error(`Enter a current demo quote for ${position.symbol} in the quotes JSON before closing.`);
    const data = await api(`/users/training/accounts/${accountId}/forex/positions/${position.id}/close/`, "POST", { midPrice: price, reason: reason || "Manager closed for training review" });
    setMessage({ kind: "ok", text: `Position closed. Realized P/L: ${money(data.realizedPnl)}` });
    await loadHistory(accountId);
    setSnapshot(null);
  });

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <div className="hidden md:block"><Sidebar /></div>
      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1500px] p-4 sm:p-6 lg:p-8">
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--accent-primary)]"><Activity size={15} /> Training Lab</div>
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Forex Demo Terminal</h1>
              <p className="mt-2 max-w-2xl text-sm text-[var(--text-secondary)]">Manager-operated practice terminal. Use public daily reference rates or enter simulated prices manually. This is not a live feed.</p>
            </div>
            <button onClick={() => runAction(async () => { await loadAccounts(); if (accountId) await loadHistory(accountId); })} disabled={busy} className="inline-flex items-center justify-center gap-2 rounded-xl border border-[var(--border-muted)] px-4 py-2.5 text-sm hover:bg-[var(--bg-hover)] disabled:opacity-50"><RefreshCw size={15} /> Refresh</button>
          </div>

          {message && <div role="status" className={`mb-5 rounded-xl border px-4 py-3 text-sm ${message.kind === "error" ? "border-red-500/30 bg-red-500/10 text-red-300" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"}`}>{message.text}</div>}

          {loading ? <div className={panel}>Loading training accounts…</div> : accounts.length === 0 ? (
            <div className={panel}><h2 className="font-semibold">No training accounts found</h2><p className="mt-2 text-sm text-[var(--text-secondary)]">Create a trainer/trainee account first in the manager API/admin workflow.</p></div>
          ) : (
            <>
              <section className={`${panel} mb-5`}>
                <div className="grid gap-4 md:grid-cols-3">
                  <div><label className={label}>Training account</label><select className={field} value={accountId} onChange={(e) => setAccountId(e.target.value)}>{accounts.map((a) => <option key={a.id} value={a.id}>{a.name} (@{a.username}) — {a.role}</option>)}</select></div>
                  <div><label className={label}>Account settings</label><div className="rounded-xl bg-[var(--bg-card-inner)] px-3 py-2.5 text-sm">1:{selected?.leverage ?? "—"} leverage · {selected?.spreadPips ?? "—"} pip spread</div></div>
                  <div><label className={label}>Account status</label><div className="flex items-center gap-2 rounded-xl bg-[var(--bg-card-inner)] px-3 py-2.5 text-sm"><span className={`h-2 w-2 rounded-full ${selected?.enabled ? "bg-emerald-500" : "bg-red-500"}`} />{selected?.enabled ? "Enabled" : "Disabled"}<span className="ml-auto text-[var(--text-secondary)]">{selected?.maxPositionSize ?? "—"} max lots</span></div></div>
                </div>
              </section>

              <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                {[
                  ["Wallet balance", snapshot?.balance ?? selected?.demoBalance ?? "—"],
                  ["Floating P/L", snapshot?.unrealizedPnl ?? "—"],
                  ["Equity", snapshot?.equity ?? "—"],
                  ["Used margin", snapshot?.usedMargin ?? "—"],
                  ["Free margin", snapshot?.freeMargin ?? "—"],
                ].map(([title, value]) => <div className={panel} key={title}><p className="text-xs text-[var(--text-secondary)]">{title}</p><p className="mt-3 break-words text-xl font-semibold tabular-nums">{title === "Wallet balance" && value !== "—" ? money(value) : title === "Floating P/L" && value !== "—" ? money(value) : title === "Equity" && value !== "—" ? money(value) : title === "Used margin" && value !== "—" ? money(value) : title === "Free margin" && value !== "—" ? money(value) : value}</p></div>)}
              </section>

              {snapshot && <div className={`mb-5 flex items-center gap-3 rounded-xl border p-3 text-sm ${snapshot.riskStatus === "NORMAL" ? "border-emerald-500/30 bg-emerald-500/5" : "border-amber-500/30 bg-amber-500/10"}`}><AlertTriangle size={18} /><span>Risk status: <strong>{snapshot.riskStatus}</strong> · Margin level: {snapshot.marginLevelPercent ? `${snapshot.marginLevelPercent}%` : "No used margin"}</span></div>}

              <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(340px,0.9fr)]">
                <section className={panel}>
                  <div className="mb-5 flex items-center gap-2"><Wallet size={18} className="text-[var(--accent-primary)]" /><h2 className="font-semibold">Practice order</h2></div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div><label className={label}>FX pair (USD quote only)</label><select className={field} value={symbol} onChange={(e) => setSymbol(e.target.value)}>{["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY"].filter((pair) => pair.endsWith("USD")).map((pair) => <option key={pair}>{pair}</option>)}</select></div>
                    <div><label className={label}>Side</label><div className="grid grid-cols-2 gap-2"><button onClick={() => setSide("BUY")} className={`flex items-center justify-center gap-2 rounded-xl border p-2.5 text-sm ${side === "BUY" ? "border-emerald-500 bg-emerald-500/10 text-emerald-400" : "border-[var(--border-muted)]"}`}><ArrowUpRight size={16} /> BUY</button><button onClick={() => setSide("SELL")} className={`flex items-center justify-center gap-2 rounded-xl border p-2.5 text-sm ${side === "SELL" ? "border-red-500 bg-red-500/10 text-red-400" : "border-[var(--border-muted)]"}`}><ArrowDownRight size={16} /> SELL</button></div></div>
                    <div><label className={label}>Lots</label><input className={field} type="number" min="0.0001" step="0.01" value={lots} onChange={(e) => setLots(e.target.value)} /></div>
                    <div><label className={label}>Demo mid-price</label><input className={field} type="number" min="0.000001" step="0.00001" value={midPrice} onChange={(e) => setMidPrice(e.target.value)} /></div>
                    <div className="sm:col-span-2"><label className={label}>Reason / lesson note (required)</label><input className={field} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={5000} /></div>
                    <div className="sm:col-span-2 rounded-xl border border-[var(--border-muted)] p-3"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm font-medium">{quoteSource}</p><p className="mt-1 text-xs text-[var(--text-secondary)]">{quoteUpdatedAt ? "Last reference update: " + quoteUpdatedAt : "No reference rates loaded this session."}</p></div><button type="button" onClick={loadReferenceRates} disabled={busy} className="rounded-lg border border-[var(--border-muted)] px-3 py-2 text-xs hover:bg-[var(--bg-hover)] disabled:opacity-50">Load public reference rates</button></div></div><div className="sm:col-span-2"><label className={label}>Demo quotes JSON (used for floating P/L and free-margin checks)</label><textarea className={`${field} min-h-20 font-mono text-xs`} value={quotesText} onChange={(e) => setQuotesText(e.target.value)} spellCheck={false} /></div>
                  </div>
                  <button onClick={openPosition} disabled={busy || !selected?.enabled} className="mt-5 w-full rounded-xl bg-[var(--accent-primary)] px-4 py-3 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50">{busy ? "Working…" : `Open demo ${side}`}</button>
                  <button onClick={refreshSnapshot} disabled={busy} className="mt-2 w-full rounded-xl border border-[var(--border-muted)] px-4 py-2.5 text-sm hover:bg-[var(--bg-hover)] disabled:opacity-50">Recalculate equity & risk</button><label className="mt-3 flex items-center gap-2 text-xs text-[var(--text-secondary)]"><input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />Auto-refresh floating P/L every 5 seconds using the quotes above</label>
                  <p className="mt-3 text-xs leading-5 text-[var(--text-secondary)]"><ShieldCheck size={13} className="mr-1 inline" />Virtual funds only. No broker order is sent. Prices can be entered manually or populated from daily public reference rates; auto-refresh recalculates using those same rates.</p>
                </section>

                <section className={panel}>
                  <div className="mb-4 flex items-center justify-between"><h2 className="font-semibold">Open positions</h2><span className="rounded-full bg-[var(--bg-muted)] px-2.5 py-1 text-xs">{positions.filter((p) => p.status === "OPEN").length} open</span></div>
                  <div className="space-y-3">
                    {positions.filter((p) => p.status === "OPEN").length === 0 ? <p className="rounded-xl bg-[var(--bg-card-inner)] p-4 text-sm text-[var(--text-secondary)]">No open Forex demo positions yet.</p> : positions.filter((p) => p.status === "OPEN").map((p) => <div key={p.id} className="rounded-xl border border-[var(--border-muted)] p-3"><div className="flex items-start justify-between gap-3"><div><div className="font-semibold">{p.symbol} <span className={p.side === "BUY" ? "text-emerald-400" : "text-red-400"}>{p.side}</span></div><p className="mt-1 text-xs text-[var(--text-secondary)]">{p.lots} lots · Entry {p.entryPrice}</p><p className="mt-1 text-xs text-[var(--text-secondary)]">Margin {money(p.marginUsed)} · 1:{p.leverage}</p></div><div className="flex flex-wrap gap-2"><button onClick={() => editForexPosition(p)} disabled={busy} className="rounded-lg border border-[var(--border-muted)] px-3 py-2 text-xs disabled:opacity-50">Edit / correct</button><button onClick={() => closePosition(p)} disabled={busy} className="rounded-lg border border-red-500/30 px-3 py-2 text-xs text-red-400 hover:bg-red-500/10 disabled:opacity-50">Close</button></div></div></div>)}
                  </div>
                  <div className="mt-6 border-t border-[var(--border-muted)] pt-4">
                    <h3 className="mb-3 text-sm font-semibold">Closed trade history & corrections</h3>
                    <div className="space-y-2">
                      {positions.filter((p) => p.status === "CLOSED").length === 0 ? <p className="text-xs text-[var(--text-secondary)]">No closed trades yet.</p> : positions.filter((p) => p.status === "CLOSED").map((p) => <div key={p.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--border-muted)] p-3 text-xs"><div><p className="font-semibold">{p.symbol} · {p.side} · {p.lots} lots</p><p className="mt-1 text-[var(--text-secondary)]">Entry {p.entryPrice} · P/L {money(p.realizedPnl)} · Closed {p.closedAt ? new Date(p.closedAt).toLocaleString() : "—"}</p></div><button onClick={() => editForexPosition(p)} disabled={busy} className="rounded-lg border border-[var(--border-muted)] px-3 py-2 disabled:opacity-50">Edit / correct</button></div>)}
                    </div>
                  </div>
                  <div className="mt-6 border-t border-[var(--border-muted)] pt-4"><h3 className="mb-3 text-sm font-semibold">Recent Forex events</h3><div className="space-y-2">{events.slice(0, 6).length === 0 ? <p className="text-xs text-[var(--text-secondary)]">No event history yet.</p> : events.slice(0, 6).map((event) => <div key={event.id} className="flex items-start justify-between gap-3 text-xs"><div><p className="font-medium">{event.eventType} · {event.symbol} · {event.side}</p><p className="mt-1 text-[var(--text-secondary)]">{event.reason}</p><p className="mt-1 text-[var(--text-muted)]">{event.actor || "Manager"} · {new Date(event.createdAt).toLocaleString()}</p></div><span className="shrink-0 tabular-nums">{money(event.pnl)}</span></div>)}</div></div>
                </section>

              </div>

              <section className={`${panel} mt-5`}>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
                  <div><div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent-primary)]">Classroom mode</div><h2 className="mt-1 text-lg font-semibold">Editable teaching board</h2><p className="mt-1 max-w-3xl text-sm text-[var(--text-secondary)]">Trainer lesson examples: symbol (USDJPY, BTCUSD, USDBTC), BUY/SELL, date/time, margin, price and explanation can be edited. These cards never change the virtual wallet or executed trade history.</p></div>
                  <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs text-amber-300">Teaching examples only</span>
                </div>
                <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div><label className={label}>Symbol</label><input className={field} value={boardSymbol} onChange={(e) => setBoardSymbol(e.target.value.toUpperCase())} placeholder="USDJPY / BTCUSD" maxLength={12}/></div>
                  <div><label className={label}>Side</label><select className={field} value={boardSide} onChange={(e) => setBoardSide(e.target.value as "BUY" | "SELL")}><option value="BUY">BUY</option><option value="SELL">SELL</option></select></div>
                  <div><label className={label}>Example entry price</label><input className={field} type="number" min="0.00000001" step="any" value={boardPrice} onChange={(e) => setBoardPrice(e.target.value)}/></div>
                  <div><label className={label}>Margin amount (display)</label><input className={field} type="number" min="0" step="0.01" value={boardMargin} onChange={(e) => setBoardMargin(e.target.value)}/></div>
                  <div><label className={label}>Leverage</label><input className={field} type="number" min="1" max="5000" value={boardLeverage} onChange={(e) => setBoardLeverage(e.target.value)}/></div>
                  <div><label className={label}>Lots (display)</label><input className={field} type="number" min="0.0001" step="0.01" value={boardLots} onChange={(e) => setBoardLots(e.target.value)}/></div>
                  <div><label className={label}>Board status</label><select className={field} value={boardStatus} onChange={(e) => setBoardStatus(e.target.value)}><option value="EXAMPLE">Teaching example</option><option value="OPEN">Open example</option><option value="CLOSED">Closed example</option></select></div>
                  <div><label className={label}>Trade date & time</label><input className={field} type="datetime-local" value={boardTime} onChange={(e) => setBoardTime(e.target.value)}/></div>
                  <div className="md:col-span-2 xl:col-span-4"><label className={label}>Lesson title</label><input className={field} value={boardTitle} onChange={(e) => setBoardTitle(e.target.value)} maxLength={160} placeholder="Example: USDJPY breakout setup"/></div>
                  <div className="md:col-span-2 xl:col-span-4"><label className={label}>Trainer explanation / correction</label><textarea className={`${field} min-h-20`} value={boardExplanation} onChange={(e) => setBoardExplanation(e.target.value)} maxLength={10000} placeholder="Explain why entry, side, margin or timing is being demonstrated."/></div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2"><button onClick={saveBoardCard} disabled={busy || !accountId} className="rounded-xl bg-[var(--accent-primary)] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Saving…" : editingCardId ? "Save teaching card" : "Add teaching card"}</button>{editingCardId && <button onClick={resetBoardForm} disabled={busy} className="rounded-xl border border-[var(--border-muted)] px-4 py-2.5 text-sm">Cancel edit</button>}</div>
                <div className="mt-6 grid gap-3 lg:grid-cols-2">
                  {boardCards.length === 0 ? <p className="rounded-xl border border-dashed border-[var(--border-muted)] p-4 text-sm text-[var(--text-secondary)]">No teaching cards yet. Create one above to use this page as a class board.</p> : boardCards.map((card) => <article key={card.id} className="rounded-xl border border-[var(--border-muted)] bg-[var(--bg-card-inner)] p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex flex-wrap items-center gap-2"><h3 className="text-lg font-semibold">{card.symbol}</h3><span className={`rounded-md px-2 py-1 text-xs font-semibold ${card.side === "BUY" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>{card.side}</span><span className="rounded-md bg-amber-500/10 px-2 py-1 text-xs text-amber-300">{card.status === "EXAMPLE" ? "TEACHING EXAMPLE" : card.status}</span></div><p className="mt-2 text-sm font-medium">{card.lessonTitle || "Untitled lesson"}</p><p className="mt-1 text-xs text-[var(--text-secondary)]">{new Date(card.tradeTime).toLocaleString()}</p></div><div className="flex gap-2"><button onClick={() => editBoardCard(card)} className="rounded-lg border border-[var(--border-muted)] px-3 py-2 text-xs">Edit</button><button onClick={() => deleteBoardCard(card)} disabled={busy} className="rounded-lg border border-red-500/30 px-3 py-2 text-xs text-red-400 disabled:opacity-50">Delete</button></div></div>
                    <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4"><div><p className="text-xs text-[var(--text-secondary)]">Example price</p><p className="mt-1 font-medium tabular-nums">{card.entryPrice}</p></div><div><p className="text-xs text-[var(--text-secondary)]">Margin</p><p className="mt-1 font-medium">{money(card.marginAmount)}</p></div><div><p className="text-xs text-[var(--text-secondary)]">Leverage</p><p className="mt-1 font-medium">1:{card.leverage}</p></div><div><p className="text-xs text-[var(--text-secondary)]">Lots</p><p className="mt-1 font-medium">{card.lots}</p></div></div>
                    {card.explanation && <p className="mt-3 whitespace-pre-wrap text-sm text-[var(--text-secondary)]">{card.explanation}</p>}
                  </article>)}
                </div>
              </section>
            </>
          )}
          <p className="mt-6 text-xs text-[var(--text-muted)]">{ "Educational demo only · Manual or daily reference prices · USD-quoted pairs only · Not connected to a live broker or financial account." }</p>
        </div>
      </main>
    </div>
  );
}
