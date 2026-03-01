"use client";

import { Job, LinkedInPost } from "@/lib/types";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    PieChart, Pie, Cell, ResponsiveContainer, Legend,
} from "recharts";

interface Props {
    jobs: Job[];
    posts: LinkedInPost[];
}

const SCORE_BUCKETS = [
    { range: "0–20", min: 0, max: 20 },
    { range: "21–40", min: 21, max: 40 },
    { range: "41–60", min: 41, max: 60 },
    { range: "61–80", min: 61, max: 80 },
    { range: "81–100", min: 81, max: 100 },
];

const ROLE_COLORS: Record<string, string> = {
    data_engineer: "#3b82f6",
    ai_engineer: "#8b5cf6",
    ml_engineer: "#6366f1",
    nlp_engineer: "#14b8a6",
    cv_engineer: "#06b6d4",
    data_scientist: "#ec4899",
};

const SOURCE_COLORS = ["#3b82f6", "#8b5cf6", "#14b8a6", "#f59e0b", "#ef4444", "#10b981", "#6366f1", "#f97316"];

export default function AnalyticsPage({ jobs, posts }: Props) {
    if (jobs.length === 0) {
        return (
            <div className="text-center py-24 text-slate-500">
                <div className="text-5xl mb-4">📊</div>
                <p className="text-lg">No jobs loaded yet — run the scraper first.</p>
            </div>
        );
    }

    // Score distribution
    const scoreData = SCORE_BUCKETS.map((b) => ({
        range: b.range,
        count: jobs.filter((j) => j.score >= b.min && j.score <= b.max).length,
    }));

    // Jobs by source (top 8)
    const sourceCounts: Record<string, number> = {};
    for (const job of jobs) {
        sourceCounts[job.source] = (sourceCounts[job.source] || 0) + 1;
    }
    const sourceData = Object.entries(sourceCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([name, count]) => ({ name, count }));

    // Jobs by role
    const roleCounts: Record<string, number> = {};
    for (const job of jobs) {
        const r = job.role_category || "other";
        roleCounts[r] = (roleCounts[r] || 0) + 1;
    }
    const roleData = Object.entries(roleCounts).map(([name, value]) => ({ name, value }));

    // Job type breakdown
    const typeMap: Record<string, number> = {};
    for (const job of jobs) {
        typeMap[job.job_type] = (typeMap[job.job_type] || 0) + 1;
    }
    const typeData = Object.entries(typeMap).map(([name, value]) => ({
        name: name.replace(/_/g, " "),
        value,
    }));

    // Application funnel
    const applied = jobs.filter((j) => j.applied).length;
    const saved = jobs.filter((j) => j.saved).length;
    const highScore = jobs.filter((j) => j.score >= 80).length;
    const withEmail = posts.filter((p) => p.contact_email).length;

    const applyRate = jobs.length ? ((applied / jobs.length) * 100).toFixed(1) : "0";
    const avgSalary = (() => {
        const withSal = jobs.filter((j) => j.salary);
        if (!withSal.length) return "N/A";
        const avg = withSal.reduce((s, j) => s + (j.salary || 0), 0) / withSal.length;
        return `$${Math.round(avg / 1000)}k`;
    })();

    return (
        <div className="space-y-8">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                    { label: "Total Jobs", value: jobs.length, color: "text-blue-400", bg: "from-blue-900/40 to-blue-800/20" },
                    { label: "Score 80+", value: highScore, color: "text-green-400", bg: "from-green-900/40 to-green-800/20" },
                    { label: "Apply Rate", value: `${applyRate}%`, color: "text-yellow-400", bg: "from-yellow-900/40 to-yellow-800/20" },
                    { label: "Avg Salary", value: avgSalary, color: "text-emerald-400", bg: "from-emerald-900/40 to-emerald-800/20" },
                    { label: "Applied", value: applied, color: "text-sky-400", bg: "from-sky-900/40 to-sky-800/20" },
                    { label: "Saved", value: saved, color: "text-pink-400", bg: "from-pink-900/40 to-pink-800/20" },
                    { label: "LI Posts", value: posts.length, color: "text-violet-400", bg: "from-violet-900/40 to-violet-800/20" },
                    { label: "Posts w/ Email", value: withEmail, color: "text-orange-400", bg: "from-orange-900/40 to-orange-800/20" },
                ].map((kpi) => (
                    <div
                        key={kpi.label}
                        className={`bg-gradient-to-br ${kpi.bg} border border-slate-700 rounded-xl p-4 text-center`}
                    >
                        <div className={`text-3xl font-bold ${kpi.color}`}>{kpi.value}</div>
                        <div className="text-xs text-slate-400 mt-1">{kpi.label}</div>
                    </div>
                ))}
            </div>

            {/* Charts row 1 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Score distribution bar */}
                <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-slate-300 mb-4">Score Distribution</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={scoreData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis dataKey="range" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                            <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                            <Tooltip
                                contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
                                labelStyle={{ color: "#e2e8f0" }}
                            />
                            <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Jobs by source */}
                <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-slate-300 mb-4">Jobs by Source</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <BarChart
                            data={sourceData}
                            layout="vertical"
                            margin={{ top: 0, right: 20, left: 20, bottom: 0 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                            <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} width={90} />
                            <Tooltip
                                contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
                            />
                            <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                                {sourceData.map((_, i) => (
                                    <Cell key={i} fill={SOURCE_COLORS[i % SOURCE_COLORS.length]} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Charts row 2 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Role breakdown pie */}
                <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-slate-300 mb-4">Jobs by Role</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <PieChart>
                            <Pie
                                data={roleData}
                                cx="50%"
                                cy="50%"
                                outerRadius={80}
                                dataKey="value"
                                label={({ name, percent }) =>
                                    `${name.replace(/_/g, " ")} ${(percent * 100).toFixed(0)}%`
                                }
                                labelLine={false}
                            >
                                {roleData.map((entry, i) => (
                                    <Cell key={i} fill={ROLE_COLORS[entry.name] || "#64748b"} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                {/* Job type breakdown pie */}
                <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-slate-300 mb-4">Job Type Breakdown</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <PieChart>
                            <Pie
                                data={typeData}
                                cx="50%"
                                cy="50%"
                                outerRadius={80}
                                dataKey="value"
                                label={({ name, value }) => `${name}: ${value}`}
                                labelLine={false}
                            >
                                {typeData.map((_, i) => (
                                    <Cell key={i} fill={SOURCE_COLORS[i % SOURCE_COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
                            />
                            <Legend
                                formatter={(value) => (
                                    <span style={{ color: "#94a3b8", fontSize: 12 }}>{value}</span>
                                )}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Top skills heatmap */}
            <SkillsHeatmap jobs={jobs} />
        </div>
    );
}

function SkillsHeatmap({ jobs }: { jobs: Job[] }) {
    const skillCount: Record<string, number> = {};
    for (const job of jobs) {
        for (const skill of job.skills ?? []) {
            skillCount[skill] = (skillCount[skill] || 0) + 1;
        }
    }
    const topSkills = Object.entries(skillCount)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 30);

    if (topSkills.length === 0) return null;

    const max = topSkills[0][1];

    return (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">
                Top Skills in Demand (from AI-scored jobs)
            </h3>
            <div className="flex flex-wrap gap-2">
                {topSkills.map(([skill, count]) => {
                    const intensity = count / max;
                    const opacity = 0.3 + intensity * 0.7;
                    return (
                        <span
                            key={skill}
                            className="px-3 py-1 rounded-full text-sm font-medium text-white transition-transform hover:scale-105"
                            style={{ background: `rgba(59, 130, 246, ${opacity})` }}
                            title={`${count} job mentions`}
                        >
                            {skill}
                            <span className="ml-1.5 text-xs opacity-70">{count}</span>
                        </span>
                    );
                })}
            </div>
        </div>
    );
}
