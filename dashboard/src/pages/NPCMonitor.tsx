import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/nexus";
import type { EmotionalState, MemoryEntry, NPC, NPCBehaviour } from "../api/nexus";
import { BehaviourBadge } from "../components/BehaviourBadge";
import { EmotionBar } from "../components/EmotionBar";
import { LiveIndicator } from "../components/LiveIndicator";
import { MemoryLog } from "../components/MemoryLog";
import { useNexusWS } from "../hooks/useNexusWS";

const BARS: Array<{ key: keyof EmotionalState; label: string; colour: string }> = [
  { key: "stress",      label: "Stress",      colour: "bg-red"    },
  { key: "trust",       label: "Trust",       colour: "bg-green"  },
  { key: "suspicion",   label: "Suspicion",   colour: "bg-yellow" },
  { key: "cooperation", label: "Cooperation", colour: "bg-blue"   },
];

export default function NPCMonitor() {
  const { sessionId, npcId } = useParams<{ sessionId: string; npcId: string }>();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(sessionId ?? null);
  const [npc, setNpc]         = useState<NPC | null>(null);
  const [state, setState]     = useState<EmotionalState | null>(null);
  const [behaviour, setBehaviour] = useState<NPCBehaviour>("cooperative");
  const [memory, setMemory]   = useState<MemoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNpcId, setSelectedNpcId] = useState<string | null>(npcId ?? null);
  const [sessionNpcs, setSessionNpcs]     = useState<NPC[]>([]);

  useEffect(() => {
    if (sessionId) {
      setActiveSessionId(sessionId);
      return;
    }
    const checkLatest = () => {
      api.sessions.list().then((list) => {
        if (list && list.length > 0) {
          setActiveSessionId((prev) => (prev !== list[0].id ? list[0].id : prev));
        }
      }).catch(() => {});
    };
    checkLatest();
    const timer = setInterval(checkLatest, 3000);
    return () => clearInterval(timer);
  }, [sessionId]);

  const { connected, lastNpcUpdate } = useNexusWS(activeSessionId);

  useEffect(() => {
    if (!activeSessionId) return;
    api.npcs.listInSession(activeSessionId)
      .then((npcs) => {
        setSessionNpcs(npcs);
        if (!selectedNpcId && npcs.length > 0) setSelectedNpcId(npcs[0]?.id ?? null);
      })
      .catch(() => {});
  }, [activeSessionId, selectedNpcId]);

  useEffect(() => {
    if (!selectedNpcId) return;
    setLoading(true);
    Promise.all([api.npcs.get(selectedNpcId), api.npcs.getMemory(selectedNpcId, 20)])
      .then(([npcData, memData]) => {
        setNpc(npcData);
        setState(npcData.current_emotional_state);
        setBehaviour(npcData.current_behaviour);
        setMemory(memData.entries);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedNpcId]);

  useEffect(() => {
    if (!selectedNpcId) return;
    // Auto-poll every 1.5s to ensure instantaneous sync with terminal
    const interval = setInterval(() => {
      Promise.all([api.npcs.get(selectedNpcId), api.npcs.getMemory(selectedNpcId, 20)])
        .then(([npcData, memData]) => {
          setState(npcData.current_emotional_state);
          setBehaviour(npcData.current_behaviour);
          setMemory(memData.entries);
        })
        .catch(() => {});
    }, 1500);
    return () => clearInterval(interval);
  }, [selectedNpcId]);

  useEffect(() => {
    if (!lastNpcUpdate || lastNpcUpdate.npc_id !== selectedNpcId) return;
    setState(lastNpcUpdate.emotional_state);
    setBehaviour(lastNpcUpdate.behaviour);
    api.npcs.getMemory(selectedNpcId, 20)
      .then((memData) => setMemory(memData.entries))
      .catch(() => {});
  }, [lastNpcUpdate, selectedNpcId]);

  if (!activeSessionId) {
    return (
      <div className="p-6 text-xs text-ink-3">
        No active session found. Start an interrogation first!
      </div>
    );
  }

  return (
    <div>
      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="text-[15px] font-semibold text-ink">NPC Monitor</h1>
          <p className="text-xs text-ink-3 mt-0.5 font-mono">{activeSessionId?.slice(0, 8)}…</p>
        </div>
        <LiveIndicator live={connected} />
      </div>

      <div className="px-6">
        {/* NPC tabs */}
        {sessionNpcs.length > 1 && (
          <div className="flex gap-1 mb-4 p-0.5 bg-raised border border-border rounded-lg w-fit">
            {sessionNpcs.map((n) => (
              <button
                key={n.id}
                onClick={() => setSelectedNpcId(n.id)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  selectedNpcId === n.id
                    ? "bg-hover text-ink shadow-sm"
                    : "text-ink-3 hover:text-ink-2"
                }`}
              >
                {n.name}
              </button>
            ))}
          </div>
        )}

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <div key={i} className="h-12 card animate-pulse" />)}
          </div>
        ) : !npc ? (
          <div className="text-center py-20 text-ink-3 text-sm">
            No NPCs found in this session.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left */}
            <div className="space-y-3">
              <div className="card p-4">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="font-medium text-ink">{npc.name}</p>
                    <p className="text-xs text-ink-3 mt-0.5">Emotional state</p>
                  </div>
                  <BehaviourBadge behaviour={behaviour} />
                </div>
                <div className="space-y-3.5">
                  {BARS.map(({ key, label, colour }) => (
                    <EmotionBar key={key} label={label} value={state?.[key] ?? 0} colour={colour} />
                  ))}
                </div>
              </div>

              {npc.personality?.scenario && (
                <div className="card p-4 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-border">
                    <div className="flex items-center gap-2">
                      <span className="text-2xs font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-blue/10 text-blue border border-blue/20">
                        {npc.personality.scenario.case_number || "DOSSIER"}
                      </span>
                      <p className="text-xs font-semibold text-ink">{npc.personality.scenario.title || "Case Incident"}</p>
                    </div>
                    {npc.personality.scenario.location && (
                      <span className="text-2xs text-ink-3 font-mono truncate max-w-[180px]">{npc.personality.scenario.location}</span>
                    )}
                  </div>

                  {npc.personality.scenario.summary && (
                    <div>
                      <p className="text-2xs uppercase tracking-wider font-semibold text-ink-3 mb-1">Incident Overview</p>
                      <p className="text-xs text-ink-2 leading-relaxed bg-raised/50 p-2.5 rounded border border-border">
                        {npc.personality.scenario.summary}
                      </p>
                    </div>
                  )}

                  {npc.personality.scenario.suspect_alibi && (
                    <div className="p-2.5 rounded bg-yellow/10 border border-yellow/20">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-yellow" />
                        <p className="text-2xs uppercase tracking-wider font-semibold text-yellow">Suspect Claimed Alibi</p>
                      </div>
                      <p className="text-xs text-ink-2 italic leading-relaxed">
                        "{npc.personality.scenario.suspect_alibi}"
                      </p>
                    </div>
                  )}

                  {npc.personality.scenario.known_leads && npc.personality.scenario.known_leads.length > 0 && (
                    <div>
                      <p className="text-2xs uppercase tracking-wider font-semibold text-ink-3 mb-1.5">Forensic Leads & Evidence</p>
                      <ul className="space-y-1.5">
                        {npc.personality.scenario.known_leads.map((lead, idx) => (
                          <li key={idx} className="text-xs text-ink-2 flex items-start gap-2 bg-raised/40 p-2 rounded border border-border/40">
                            <span className="text-blue font-mono font-bold text-2xs mt-0.5">•</span>
                            <span className="leading-snug">{lead}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {npc.personality.scenario.objectives && npc.personality.scenario.objectives.length > 0 && (
                    <div>
                      <p className="text-2xs uppercase tracking-wider font-semibold text-ink-3 mb-1">Investigation Objectives</p>
                      <ul className="space-y-1">
                        {npc.personality.scenario.objectives.map((obj, idx) => (
                          <li key={idx} className="text-xs text-ink-2 flex items-start gap-1.5">
                            <span className="text-green font-bold text-2xs mt-0.5">✓</span>
                            <span className="leading-snug">{obj}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {lastNpcUpdate?.secret_leaked && (
                <div className="card p-3 border-red/25 bg-red/5">
                  <p className="text-xs text-red font-medium">Secret revealed</p>
                  <p className="text-xs text-ink-2 mt-0.5">{lastNpcUpdate.secret_leaked}</p>
                </div>
              )}

              <div className="card p-3">
                <p className="text-2xs text-ink-3 mb-2 font-medium uppercase tracking-wider">Raw state</p>
                <pre className="text-2xs text-green font-mono whitespace-pre-wrap overflow-auto max-h-36 leading-relaxed">
                  {JSON.stringify(state, null, 2)}
                </pre>
              </div>
            </div>

            {/* Right */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-4">
                <p className="font-medium text-ink text-sm">Interaction history</p>
                <span className="text-2xs text-ink-3">{memory.length} entries</span>
              </div>
              <MemoryLog entries={memory} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
