"use client";

import { Job, LinkedInPost } from "@/lib/types";

interface Props {
  jobs: Job[];
  posts: LinkedInPost[];
}

export default function StatsBar({ jobs, posts }: Props) {
  const total = jobs.length;
  const avgScore = total
    ? Math.round(jobs.reduce((s, j) => s + j.score, 0) / total)
    : 0;
  const withSalary = jobs.filter((j) => j.salary).length;
  const contracts = jobs.filter((j) =>
    j.job_type.includes("contract")
  ).length;
  const fullTime = jobs.filter((j) => j.job_type === "full_time").length;
  const applied = jobs.filter((j) => j.applied).length;
  const saved = jobs.filter((j) => j.saved).length;
  const highScore = jobs.filter((j) => j.score >= 80).length;

  const stats = [
    { label: "Total Jobs", value: total, color: "text-blue-400" },
    { label: "Avg Score", value: avgScore, color: "text-green-400" },
    { label: "Score 80+", value: highScore, color: "text-yellow-400" },
    { label: "Full-Time", value: fullTime, color: "text-purple-400" },
    { label: "Contract", value: contracts, color: "text-orange-400" },
    { label: "With Salary", value: withSalary, color: "text-emerald-400" },
    { label: "Applied", value: applied, color: "text-sky-400" },
    { label: "Saved", value: saved, color: "text-pink-400" },
    { label: "LI Posts", value: posts.length, color: "text-indigo-400" },
  ];

  return (
    <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-2 mb-6">
      {stats.map((s) => (
        <div
          key={s.label}
          className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-center"
        >
          <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
          <div className="text-xs text-slate-400 mt-1">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
