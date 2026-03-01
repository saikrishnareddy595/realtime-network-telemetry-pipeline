"use client";

import { Filters, JobType, RoleCategory } from "@/lib/types";

interface Props {
  filters: Filters;
  sources: string[];
  onChange: (f: Filters) => void;
}

const ROLES: { value: RoleCategory; label: string }[] = [
  { value: "all", label: "All Roles" },
  { value: "data_engineer", label: "Data Engineer" },
  { value: "ai_engineer", label: "AI Engineer" },
  { value: "ml_engineer", label: "ML Engineer" },
  { value: "nlp_engineer", label: "NLP Engineer" },
  { value: "cv_engineer", label: "CV Engineer" },
  { value: "data_scientist", label: "Data Scientist" },
];

const JOB_TYPES: { value: JobType; label: string }[] = [
  { value: "full_time", label: "Full-Time" },
  { value: "contract", label: "Contract" },
  { value: "contract_to_hire", label: "Contract-to-Hire" },
  { value: "part_time", label: "Part-Time" },
];

const SORT_OPTIONS = [
  { value: "score", label: "Score" },
  { value: "date", label: "Date" },
  { value: "salary", label: "Salary" },
];

export default function FilterSidebar({ filters, sources, onChange }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });

  const toggleJobType = (t: JobType) => {
    const next = filters.jobTypes.includes(t)
      ? filters.jobTypes.filter((x) => x !== t)
      : [...filters.jobTypes, t];
    set({ jobTypes: next });
  };

  const toggleSource = (s: string) => {
    const next = filters.sources.includes(s)
      ? filters.sources.filter((x) => x !== s)
      : [...filters.sources, s];
    set({ sources: next });
  };

  return (
    <aside className="w-64 flex-shrink-0 bg-slate-800 border border-slate-700 rounded-xl p-4 space-y-6 h-fit sticky top-4">
      {/* Search */}
      <div>
        <label className="block text-xs font-semibold text-slate-400 uppercase mb-2">
          Search
        </label>
        <input
          type="text"
          value={filters.search}
          onChange={(e) => set({ search: e.target.value })}
          placeholder="Title, company…"
          className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Role */}
      <div>
        <label className="block text-xs font-semibold text-slate-400 uppercase mb-2">
          Role Category
        </label>
        <div className="space-y-1">
          {ROLES.map((r) => (
            <button
              key={r.value}
              onClick={() => set({ role: r.value })}
              className={`w-full text-left px-3 py-1.5 rounded-lg text-sm transition-colors ${
                filters.role === r.value
                  ? "bg-blue-600 text-white"
                  : "text-slate-300 hover:bg-slate-700"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Job Type */}
      <div>
        <label className="block text-xs font-semibold text-slate-400 uppercase mb-2">
          Job Type
        </label>
        <div className="space-y-1">
          {JOB_TYPES.map((t) => (
            <label key={t.value} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.jobTypes.includes(t.value)}
                onChange={() => toggleJobType(t.value)}
                className="accent-blue-500"
              />
              <span className="text-sm text-slate-300">{t.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Min Score */}
      <div>
        <label className="block text-xs font-semibold text-slate-400 uppercase mb-2">
          Min Score: <span className="text-blue-400">{filters.minScore}</span>
        </label>
        <input
          type="range"
          min={0}
          max={100}
          value={filters.minScore}
          onChange={(e) => set({ minScore: Number(e.target.value) })}
          className="w-full accent-blue-500"
        />
      </div>

      {/* Sort */}
      <div>
        <label className="block text-xs font-semibold text-slate-400 uppercase mb-2">
          Sort By
        </label>
        <select
          value={filters.sortBy}
          onChange={(e) =>
            set({ sortBy: e.target.value as Filters["sortBy"] })
          }
          className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {/* Toggles */}
      <div className="space-y-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.remoteOnly}
            onChange={(e) => set({ remoteOnly: e.target.checked })}
            className="accent-blue-500"
          />
          <span className="text-sm text-slate-300">Remote Only</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.easyApplyOnly}
            onChange={(e) => set({ easyApplyOnly: e.target.checked })}
            className="accent-blue-500"
          />
          <span className="text-sm text-slate-300">Easy Apply Only</span>
        </label>
      </div>

      {/* Sources */}
      {sources.length > 0 && (
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase mb-2">
            Sources
          </label>
          <div className="space-y-1 max-h-40 overflow-y-auto scrollbar-thin">
            {sources.map((s) => (
              <label key={s} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={
                    filters.sources.length === 0 || filters.sources.includes(s)
                  }
                  onChange={() => toggleSource(s)}
                  className="accent-blue-500"
                />
                <span className="text-xs text-slate-400">{s}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Reset */}
      <button
        onClick={() =>
          onChange({
            role: "all",
            jobTypes: [],
            sources: [],
            minScore: 0,
            remoteOnly: false,
            easyApplyOnly: false,
            search: "",
            sortBy: "score",
          })
        }
        className="w-full text-xs text-slate-500 hover:text-slate-300 py-1 transition-colors"
      >
        Reset filters
      </button>
    </aside>
  );
}
