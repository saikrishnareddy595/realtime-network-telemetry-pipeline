"use client";

import { useState } from "react";
import { Job } from "@/lib/types";

type KanbanStatus = "saved" | "applied" | "phone_screen" | "technical" | "offer" | "rejected";

const COLUMNS: { id: KanbanStatus; label: string; color: string; icon: string }[] = [
    { id: "saved", label: "Saved", color: "border-pink-600", icon: "★" },
    { id: "applied", label: "Applied", color: "border-blue-600", icon: "📤" },
    { id: "phone_screen", label: "Phone Screen", color: "border-yellow-500", icon: "📞" },
    { id: "technical", label: "Technical", color: "border-orange-500", icon: "💻" },
    { id: "offer", label: "Offer 🎉", color: "border-green-500", icon: "🎁" },
    { id: "rejected", label: "Rejected", color: "border-red-700", icon: "❌" },
];

interface KanbanJob extends Job {
    kanban_status?: KanbanStatus;
}

interface Props {
    jobs: Job[];
    onApplied: (id: number, applied: boolean) => void;
    onSaved: (id: number, saved: boolean) => void;
}

export default function KanbanBoard({ jobs, onApplied, onSaved }: Props) {
    // Local kanban status state (persisted in localStorage)
    const [kanbanMap, setKanbanMap] = useState<Record<number, KanbanStatus>>(() => {
        try {
            const raw = localStorage.getItem("kanban_status");
            return raw ? JSON.parse(raw) : {};
        } catch {
            return {};
        }
    });
    const [dragId, setDragId] = useState<number | null>(null);

    const setStatus = (id: number, status: KanbanStatus) => {
        const next = { ...kanbanMap, [id]: status };
        setKanbanMap(next);
        try {
            localStorage.setItem("kanban_status", JSON.stringify(next));
        } catch { }
        // Sync applied state with supabase
        if (status === "applied") onApplied(id, true);
        if (status === "saved") onSaved(id, true);
    };

    // Assign kanban status: saved first, then applied, else not tracked
    const enriched: KanbanJob[] = jobs.map((j) => ({
        ...j,
        kanban_status: kanbanMap[j.id] ?? (j.applied ? "applied" : j.saved ? "saved" : undefined),
    }));

    const tracked = enriched.filter((j) => j.kanban_status);
    const untracked = enriched.filter((j) => !j.kanban_status);

    const getColumn = (status: KanbanStatus) =>
        tracked.filter((j) => j.kanban_status === status);

    const handleDragStart = (id: number) => setDragId(id);
    const handleDrop = (status: KanbanStatus) => {
        if (dragId !== null) {
            setStatus(dragId, status);
            setDragId(null);
        }
    };

    return (
        <div className="space-y-6">
            {/* Kanban board */}
            <div className="overflow-x-auto pb-4">
                <div className="flex gap-4 min-w-max">
                    {COLUMNS.map((col) => {
                        const colJobs = getColumn(col.id);
                        return (
                            <div
                                key={col.id}
                                className={`w-60 flex-shrink-0 bg-slate-800/60 border-t-2 ${col.color} rounded-xl`}
                                onDragOver={(e) => e.preventDefault()}
                                onDrop={() => handleDrop(col.id)}
                            >
                                {/* Column header */}
                                <div className="px-3 py-2 flex items-center justify-between border-b border-slate-700">
                                    <span className="text-sm font-semibold text-slate-200">
                                        {col.icon} {col.label}
                                    </span>
                                    <span className="text-xs bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded-full">
                                        {colJobs.length}
                                    </span>
                                </div>

                                {/* Cards */}
                                <div className="p-2 space-y-2 min-h-[120px]">
                                    {colJobs.map((job) => (
                                        <KanbanCard
                                            key={job.id}
                                            job={job}
                                            onDragStart={() => handleDragStart(job.id)}
                                            onMove={(status) => setStatus(job.id, status)}
                                        />
                                    ))}
                                    {colJobs.length === 0 && (
                                        <div className="text-center py-6 text-slate-600 text-xs">
                                            Drop here
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Untracked jobs — quick-add to board */}
            {untracked.length > 0 && (
                <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
                    <h3 className="text-sm font-semibold text-slate-400 mb-3">
                        📋 Not yet tracked — click to add to board ({untracked.length} jobs)
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
                        {untracked.slice(0, 30).map((job) => (
                            <div
                                key={job.id}
                                className="flex items-center justify-between gap-2 bg-slate-700/50 rounded-lg px-3 py-2"
                            >
                                <div className="min-w-0">
                                    <p className="text-xs font-medium text-slate-200 truncate">{job.title}</p>
                                    <p className="text-xs text-slate-500 truncate">{job.company}</p>
                                </div>
                                <select
                                    onChange={(e) => setStatus(job.id, e.target.value as KanbanStatus)}
                                    defaultValue=""
                                    className="text-xs bg-slate-700 border border-slate-600 rounded px-1 py-1 text-slate-300 flex-shrink-0"
                                >
                                    <option value="" disabled>+ Track</option>
                                    {COLUMNS.map((c) => (
                                        <option key={c.id} value={c.id}>{c.label}</option>
                                    ))}
                                </select>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

function KanbanCard({
    job,
    onDragStart,
    onMove,
}: {
    job: KanbanJob;
    onDragStart: () => void;
    onMove: (s: KanbanStatus) => void;
}) {
    const scoreColor =
        job.score >= 80 ? "bg-green-500" : job.score >= 60 ? "bg-yellow-500" : "bg-orange-500";

    return (
        <div
            draggable
            onDragStart={onDragStart}
            className="bg-slate-700 rounded-lg p-2.5 cursor-grab active:cursor-grabbing border border-slate-600 hover:border-slate-400 transition-colors group"
        >
            <div className="flex items-start justify-between gap-1">
                <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-slate-100 truncate leading-tight">
                        {job.title}
                    </p>
                    <p className="text-xs text-slate-400 truncate">{job.company}</p>
                </div>
                <span
                    className={`text-white text-xs font-bold px-1.5 py-0.5 rounded ${scoreColor} flex-shrink-0`}
                >
                    {job.score}
                </span>
            </div>

            <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:underline"
                    onClick={(e) => e.stopPropagation()}
                >
                    View →
                </a>
                <span className="text-slate-600">·</span>
                <select
                    onChange={(e) => onMove(e.target.value as KanbanStatus)}
                    value={job.kanban_status || ""}
                    className="text-xs bg-slate-600 rounded px-1 py-0.5 text-slate-300 border-0"
                    onClick={(e) => e.stopPropagation()}
                >
                    {COLUMNS.map((c) => (
                        <option key={c.id} value={c.id}>{c.label}</option>
                    ))}
                </select>
            </div>
        </div>
    );
}
