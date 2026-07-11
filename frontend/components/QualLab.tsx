"use client";

import LabChat from "@/components/LabChat";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  mediaApi,
  qualApi,
  type CodeAssignment,
  type Codebook,
  type MediaAsset,
  type QuoteRow,
  type ThemeMatrix,
  type Transcript,
} from "@/lib/api";

const POLL_MS = 5000;

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-5">
      <h3 className="font-display text-lg text-forest">{title}</h3>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function StatusChip({ status }: { status: MediaAsset["status"] }) {
  const styles: Record<MediaAsset["status"], string> = {
    uploaded: "bg-bg text-ink/60 border-line",
    processing: "bg-amber-100 text-amber-800 border-amber-300",
    transcribed: "bg-leaf/15 text-forest border-leaf",
    failed: "bg-red-50 text-red-700 border-red-200",
  };
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-xs ${styles[status]}`}>{status}</span>
  );
}

export default function QualLab({ projectId }: { projectId: string }) {
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setAssets(await mediaApi.list(projectId));
  }, [projectId]);

  useEffect(() => {
    void refresh();
    const t = setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, POLL_MS);
    return () => clearInterval(t);
  }, [refresh]);

  async function upload(file: File) {
    setUploading(true);
    setErr(null);
    try {
      const asset = await mediaApi.upload(projectId, file);
      setSelected(asset.id);
      await refresh();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "upload failed");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  if (selected) {
    return (
      <TranscriptView
        assetId={selected}
        projectId={projectId}
        onBack={() => {
          setSelected(null);
          void refresh();
        }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <LabChat projectId={projectId} lab="qual" />
      <p className="text-sm text-ink/70">
        Upload interviews or testimony (audio/video) — they transcribe automatically into
        timestamped, correctable transcripts.
      </p>
      {err && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>}

      <Card title="Add media">
        <input
          ref={fileRef}
          type="file"
          accept=".mp3,.wav,.m4a,.ogg,.webm,.flac,.aac,.mp4,.mov,.mkv"
          disabled={uploading}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void upload(f);
          }}
          className="text-sm"
        />
        {uploading && <p className="mt-2 text-xs text-ink/50">Uploading…</p>}
        <p className="mt-2 text-xs text-ink/40">
          Audio transcribes directly; video needs ffmpeg on the server to extract its audio track.
        </p>
      </Card>

      <Card title={`Library (${assets.length})`}>
        {assets.length === 0 ? (
          <p className="text-sm text-ink/50">No media yet.</p>
        ) : (
          <div className="grid gap-2">
            {assets.map((a) => (
              <button
                key={a.id}
                onClick={() => setSelected(a.id)}
                className="flex items-center justify-between rounded-xl border border-line p-3 text-left hover:border-leaf"
              >
                <div>
                  <div className="text-sm font-medium text-forest">{a.filename}</div>
                  <div className="text-xs text-ink/50">
                    {a.kind}
                    {a.duration_seconds ? ` · ${Math.round(a.duration_seconds)}s` : ""}
                    {a.language ? ` · ${a.language}` : ""}
                  </div>
                  {a.status === "failed" && a.error && (
                    <div className="mt-1 text-xs text-red-600">{a.error}</div>
                  )}
                </div>
                <StatusChip status={a.status} />
              </button>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function TranscriptView({
  assetId,
  projectId,
  onBack,
}: {
  assetId: string;
  projectId: string;
  onBack: () => void;
}) {
  const [asset, setAsset] = useState<MediaAsset | null>(null);
  const [transcript, setTranscript] = useState<Transcript>(null);
  const [mediaUrl, setMediaUrl] = useState<string | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [assignments, setAssignments] = useState<CodeAssignment[]>([]);
  const playerRef = useRef<HTMLAudioElement | HTMLVideoElement | null>(null);

  const codesBySegment: Record<number, CodeAssignment[]> = {};
  for (const a of assignments) (codesBySegment[a.segment] ??= []).push(a);

  const load = useCallback(async () => {
    const detail = await mediaApi.get(assetId);
    setAsset(detail.asset);
    setTranscript(detail.transcript);
  }, [assetId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    let revoke: string | null = null;
    mediaApi
      .fileUrl(assetId)
      .then((url) => {
        revoke = url;
        setMediaUrl(url);
      })
      .catch(() => {});
    return () => {
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [assetId]);

  // poll while still processing
  useEffect(() => {
    if (!asset || asset.status === "transcribed" || asset.status === "failed") return;
    const t = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(t);
  }, [asset, load]);

  function seek(seconds: number) {
    if (playerRef.current) {
      playerRef.current.currentTime = seconds;
      void playerRef.current.play().catch(() => {});
    }
  }

  async function saveEdit(index: number) {
    try {
      await mediaApi.correctSegment(assetId, index, draft);
      setEditing(null);
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "correction failed");
    }
  }

  async function retry() {
    try {
      await mediaApi.retry(assetId);
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "retry failed");
    }
  }

  if (!asset) return <p className="text-sm text-ink/50">Loading…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="text-sm text-forest hover:underline">
          ← Library
        </button>
        <StatusChip status={asset.status} />
      </div>
      {err && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>}

      <Card title={asset.filename}>
        {mediaUrl &&
          (asset.kind === "video" ? (
            <video
              ref={playerRef as React.RefObject<HTMLVideoElement>}
              src={mediaUrl}
              controls
              className="w-full rounded-xl"
            />
          ) : (
            <audio
              ref={playerRef as React.RefObject<HTMLAudioElement>}
              src={mediaUrl}
              controls
              className="w-full"
            />
          ))}
        {asset.status === "failed" && (
          <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {asset.error || "transcription failed"}
            <button onClick={retry} className="ml-3 text-forest underline">
              Retry
            </button>
          </div>
        )}
        {asset.status === "processing" && (
          <p className="mt-3 text-sm text-amber-700">Transcribing…</p>
        )}
      </Card>

      {transcript && asset.status === "transcribed" && (
        <CodingPanel
          assetId={assetId}
          projectId={projectId}
          codesBySegment={codesBySegment}
          onCoded={setAssignments}
        />
      )}

      {transcript && (
        <Card title="Transcript (click a line to jump; double-click to correct)">
          <div className="max-h-[28rem] space-y-1 overflow-auto">
            {transcript.segments.map((s, i) => (
              <div key={i} className="group flex gap-3 rounded-lg px-2 py-1 hover:bg-bg">
                <button
                  onClick={() => seek(s.start)}
                  className="w-14 shrink-0 text-left font-mono text-xs text-leaf"
                  title="Jump to this moment"
                >
                  {fmt(s.start)}
                </button>
                {editing === i ? (
                  <div className="flex-1">
                    <textarea
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      rows={2}
                      className="w-full rounded-lg border border-line px-2 py-1 text-sm"
                    />
                    <div className="mt-1 flex gap-2 text-xs">
                      <button onClick={() => saveEdit(i)} className="text-forest underline">
                        Save
                      </button>
                      <button onClick={() => setEditing(null)} className="text-ink/50 underline">
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1">
                    <p
                      onDoubleClick={() => {
                        setEditing(i);
                        setDraft(s.text);
                      }}
                      className="cursor-text text-sm text-ink"
                    >
                      {s.text}
                    </p>
                    {(codesBySegment[i] ?? []).length > 0 && (
                      <div className="mt-0.5 flex flex-wrap gap-1">
                        {codesBySegment[i].map((a, j) => (
                          <span
                            key={j}
                            className={`rounded-full px-2 py-0.5 text-[10px] ${
                              a.source === "human"
                                ? "bg-forest text-white"
                                : "bg-leaf/15 text-forest"
                            }`}
                            title={a.support || a.source}
                          >
                            {a.code}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function CodingPanel({
  assetId,
  projectId,
  codesBySegment,
  onCoded,
}: {
  assetId: string;
  projectId: string;
  codesBySegment: Record<number, CodeAssignment[]>;
  onCoded: (a: CodeAssignment[]) => void;
}) {
  const [codebooks, setCodebooks] = useState<Codebook[]>([]);
  const [quotes, setQuotes] = useState<QuoteRow[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setCodebooks(await qualApi.codebooks(projectId));
    const coding = (await qualApi.coding(assetId)).coding;
    if (coding?.assignments) onCoded(coding.assignments);
  }, [projectId, assetId, onCoded]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function act(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setNote(null);
    try {
      await fn();
    } catch (e) {
      setNote(e instanceof ApiError ? e.message : `${label} failed`);
    } finally {
      setBusy(null);
    }
  }

  const approved = codebooks.filter((c) => c.status === "approved");
  const proposed = codebooks.filter((c) => c.status === "proposed");
  const coded = Object.keys(codesBySegment).length > 0;

  return (
    <Card title="Thematic coding">
      {note && <p className="mb-2 rounded-lg bg-amber-50 px-3 py-1.5 text-xs text-amber-800">{note}</p>}
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <button
          onClick={() =>
            act("propose", async () => {
              await qualApi.proposeCodebook(projectId, [assetId]);
              await refresh();
            })
          }
          disabled={busy !== null}
          className="rounded-full border border-line px-3 py-1.5 text-forest hover:bg-bg disabled:opacity-50"
        >
          {busy === "propose" ? "Proposing…" : "Propose codebook"}
        </button>
        {proposed.map((cb) => (
          <span key={cb.id} className="flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2 py-1 text-xs">
            {cb.name} ({cb.codes.length})
            <button
              onClick={() =>
                act("approve", async () => {
                  await qualApi.approveCodebook(cb.id);
                  await refresh();
                })
              }
              className="ml-1 text-forest underline"
            >
              approve
            </button>
          </span>
        ))}
        {approved.map((cb) => (
          <button
            key={cb.id}
            onClick={() =>
              act("code", async () => {
                const r = await qualApi.codeAsset(assetId, cb.id);
                onCoded(r.assignments);
              })
            }
            disabled={busy !== null}
            className="rounded-full bg-leaf px-3 py-1.5 text-white hover:bg-leaf/90 disabled:opacity-50"
          >
            {busy === "code" ? "Coding…" : `Code with “${cb.name}”`}
          </button>
        ))}
        <button
          onClick={() =>
            act("quotes", async () => {
              const r = await qualApi.quotes(assetId);
              setQuotes(r.quotes);
              setNote(
                r.dropped_non_verbatim > 0
                  ? `${r.dropped_non_verbatim} non-verbatim candidate(s) dropped — only exact words survive.`
                  : null,
              );
            })
          }
          disabled={busy !== null}
          className="rounded-full border border-line px-3 py-1.5 text-forest hover:bg-bg disabled:opacity-50"
        >
          {busy === "quotes" ? "Extracting…" : "Extract quotes"}
        </button>
      </div>
      {coded && (
        <p className="mt-2 text-xs text-ink/50">
          Codes show under each transcript line (dark = human-added). Double-check and correct freely.
        </p>
      )}
      {quotes && quotes.length > 0 && (
        <div className="mt-3 space-y-1">
          <div className="text-xs text-ink/50">Evidence-locked quotes</div>
          {quotes.map((q, i) => (
            <blockquote key={i} className="border-l-2 border-leaf pl-3 text-sm text-ink">
              “{q.text}” <span className="text-xs text-ink/40">({fmt(q.start)})</span>
            </blockquote>
          ))}
        </div>
      )}
    </Card>
  );
}

function fmt(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}
