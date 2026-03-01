"use client";

import { useState, MouseEvent } from "react";
import { Job } from "@/lib/types";

interface Props {
  job: Job;
  onApplied: (id: number, applied: boolean) => void;
  onSaved: (id: number, saved: boolean) => void;
}

const TYPE_COLORS: Record<string, string> = {
  full_time: "bg-green-900 text-green-300",
  contract: "bg-orange-900 text-orange-300",
  contract_to_hire: "bg-yellow-900 text-yellow-300",
  part_time: "bg-purple-900 text-purple-300",
};

const ROLE_COLORS: Record<string, string> = {
  data_engineer: "bg-blue-900 text-blue-300",
  ai_engineer: "bg-violet-900 text-violet-300",
  ml_engineer: "bg-indigo-900 text-indigo-300",
  nlp_engineer: "bg-teal-900 text-teal-300",
  cv_engineer: "bg-cyan-900 text-cyan-300",
  data_scientist: "bg-pink-900 text-pink-300",
};

function scoreColor(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-yellow-500";
  if (score >= 40) return "bg-orange-500";
  return "bg-red-500";
}

export default function JobCard({ job, onApplied, onSaved }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [applying, setApplying] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<"liked" | "disliked" | null>(null);

  const handleFeedback = async (liked: boolean, e: MouseEvent) => {
    e.stopPropagation();
    setFeedback(liked ? "liked" : "disliked");
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: job.id, table: "jobs", liked }),
    });
  };

  const handleApply = async (e: MouseEvent) => {
    e.stopPropagation();
    if (applying) return;
    setApplying(true);
    try {
      await fetch("/api/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: job.id, applied: !job.applied }),
      });
      onApplied(job.id, !job.applied);
    } finally {
      setApplying(false);
    }
  };

  const handleSave = async (e: MouseEvent) => {
    e.stopPropagation();
    if (saving) return;
    setSaving(true);
    try {
      await fetch("/api/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: job.id, saved: !job.saved }),
      });
      onSaved(job.id, !job.saved);
    } finally {
      setSaving(false);
    }
  };

  const typeLabel = (job.job_type || "full_time").replace(/_/g, "-");
  const roleLabel = (job.role_category || "other").replace(/_/g, " ");
  const postedDate = job.posted_date ? new Date(job.posted_date) : new Date();
  const postedDays = Math.floor(
    (Date.now() - (isNaN(postedDate.getTime()) ? Date.now() : postedDate.getTime())) / 86400000
  );


  return (
    <div
      className={`bg-slate-800 border rounded-xl p-4 transition-all cursor-pointer hover:border-slate-500 ${job.applied
        ? "border-blue-700 opacity-75"
        : job.saved
          ? "border-pink-700"
          : "border-slate-700"
        }`}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Score badge */}
            <span
              className={`inline-flex items-center justify-center w-9 h-9 rounded-lg text-white font-bold text-sm flex-shrink-0 ${scoreColor(
                job.score
              )}`}
            >
              {job.score}
            </span>
            <div>
              <h3 className="font-semibold text-slate-100 text-sm leading-tight truncate max-w-xs">
                {job.title}
              </h3>
              <p className="text-slate-400 text-xs mt-0.5">
                {job.company} &middot; {job.location}
              </p>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Feedback buttons */}
          <button
            onClick={(e) => handleFeedback(true, e)}
            title="Great fit"
            className={`p-1.5 rounded-lg text-sm transition-colors ${feedback === "liked"
              ? "bg-green-600 text-white"
              : "bg-slate-700 text-slate-400 hover:text-green-400"
              }`}
          >
            👍
          </button>
          <button
            onClick={(e) => handleFeedback(false, e)}
            title="Not for me"
            className={`p-1.5 rounded-lg text-sm transition-colors ${feedback === "disliked"
              ? "bg-red-700 text-white"
              : "bg-slate-700 text-slate-400 hover:text-red-400"
              }`}
          >
            👎
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            title={job.saved ? "Unsave" : "Save"}
            className={`p-1.5 rounded-lg text-sm transition-colors ${job.saved
              ? "bg-pink-600 text-white"
              : "bg-slate-700 text-slate-400 hover:text-pink-400"
              }`}
          >
            {job.saved ? "★" : "☆"}
          </button>
          <button
            onClick={handleApply}
            disabled={applying}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${job.applied
              ? "bg-blue-800 text-blue-300"
              : "bg-blue-600 hover:bg-blue-500 text-white"
              }`}
          >
            {job.applied ? "Applied ✓" : "Mark Applied"}
          </button>
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e: MouseEvent) => e.stopPropagation()}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors"
          >
            View →
          </a>

        </div>
      </div>


      {/* Tags row */}
      <div className="flex flex-wrap gap-1.5 mt-3">
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${TYPE_COLORS[job.job_type] || "bg-slate-700 text-slate-300"
            }`}
        >
          {typeLabel}
        </span>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${ROLE_COLORS[job.role_category] || "bg-slate-700 text-slate-300"
            }`}
        >
          {roleLabel}
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-400">
          {job.source}
        </span>
        {job.salary && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-900 text-emerald-300">
            ${job.salary.toLocaleString()}/yr
          </span>
        )}
        {job.easy_apply && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-teal-900 text-teal-300">
            Easy Apply
          </span>
        )}
        {job.applicants && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-400">
            {job.applicants} applicants
          </span>
        )}
        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-500 ml-auto">
          {postedDays === 0 ? "Today" : `${postedDays}d ago`}
        </span>
      </div>

      {/* LLM score row */}
      {typeof job.llm_score === "number" && (
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-slate-500">AI Score:</span>
          <span
            className={`text-xs font-bold ${job.llm_score >= 80
              ? "text-green-400"
              : job.llm_score >= 60
                ? "text-yellow-400"
                : "text-slate-400"
              }`}
          >
            {job.llm_score}
          </span>
          {job.llm_reason && (
            <span className="text-xs text-slate-500 truncate">
              — {job.llm_reason}
            </span>
          )}
        </div>
      )}


      {/* Skills */}
      {job.skills && job.skills.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {job.skills.slice(0, 6).map((skill: string) => (
            <span
              key={skill}
              className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded"
            >
              {skill}
            </span>
          ))}
        </div>
      )}


      {/* Expanded details */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-slate-700 space-y-2">
          {job.llm_summary && (
            <p className="text-sm text-slate-300">{job.llm_summary}</p>
          )}
          {job.description && (
            <p className="text-xs text-slate-400 leading-relaxed line-clamp-6">
              {job.description}
            </p>
          )}
          {job.notes && (
            <p className="text-xs text-yellow-400 italic">
              Notes: {job.notes}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
