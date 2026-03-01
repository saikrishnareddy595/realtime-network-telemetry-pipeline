"use client";

import { useEffect, useState, useCallback } from "react";
import { Job, LinkedInPost, Filters } from "@/lib/types";
import StatsBar from "@/components/StatsBar";
import FilterSidebar from "@/components/FilterSidebar";
import JobsGrid from "@/components/JobsGrid";
import LinkedInPosts from "@/components/LinkedInPosts";

type Tab = "jobs" | "posts" | "applied" | "saved";

const DEFAULT_FILTERS: Filters = {
  role: "all",
  jobTypes: [],
  sources: [],
  minScore: 0,
  remoteOnly: false,
  easyApplyOnly: false,
  search: "",
  sortBy: "score",
};

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [posts, setPosts] = useState<LinkedInPost[]>([]);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [activeTab, setActiveTab] = useState<Tab>("jobs");
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [jobsRes, postsRes] = await Promise.all([
        fetch("/api/jobs"),
        fetch("/api/posts"),
      ]);
      const jobsData: Job[] = await jobsRes.json();
      const postsData: LinkedInPost[] = await postsRes.json();
      setJobs(jobsData);
      setPosts(postsData);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Refresh every 15 minutes
    const interval = setInterval(fetchData, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleApplied = (id: number, applied: boolean) => {
    setJobs((prev) =>
      prev.map((j) => (j.id === id ? { ...j, applied } : j))
    );
  };

  const handleSaved = (id: number, saved: boolean) => {
    setJobs((prev) =>
      prev.map((j) => (j.id === id ? { ...j, saved } : j))
    );
  };

  const sources = Array.from(new Set(jobs.map((j) => j.source))).sort();

  const appliedJobs = jobs.filter((j) => j.applied);
  const savedJobs = jobs.filter((j) => j.saved);

  const tabJobs =
    activeTab === "applied"
      ? appliedJobs
      : activeTab === "saved"
      ? savedJobs
      : jobs;

  const TABS: { id: Tab; label: string; count?: number }[] = [
    { id: "jobs", label: "All Jobs", count: jobs.length },
    { id: "posts", label: "LinkedIn Posts", count: posts.length },
    { id: "saved", label: "Saved", count: savedJobs.length },
    { id: "applied", label: "Applied", count: appliedJobs.length },
  ];

  return (
    <main className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="max-w-screen-2xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">
              <span className="text-blue-400">Job</span>Scraper
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              AI-powered · {jobs.length} jobs · {posts.length} posts
              {lastUpdated && ` · Updated ${lastUpdated}`}
            </p>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
          >
            {loading ? (
              <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              "↻"
            )}
            Refresh
          </button>
        </div>
      </header>

      <div className="max-w-screen-2xl mx-auto px-6 py-6">
        {/* Stats */}
        <StatsBar jobs={jobs} posts={posts} />

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-slate-800 p-1 rounded-lg border border-slate-700 w-fit">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span
                  className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${
                    activeTab === tab.id
                      ? "bg-blue-500 text-white"
                      : "bg-slate-700 text-slate-400"
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Main content */}
        {activeTab === "posts" ? (
          <LinkedInPosts posts={posts} />
        ) : (
          <div className="flex gap-6">
            {/* Sidebar */}
            <FilterSidebar
              filters={filters}
              sources={sources}
              onChange={setFilters}
            />

            {/* Jobs grid */}
            <div className="flex-1 min-w-0">
              {loading && jobs.length === 0 ? (
                <div className="text-center py-16 text-slate-500">
                  <div className="inline-block w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
                  <p>Loading jobs…</p>
                </div>
              ) : (
                <JobsGrid
                  jobs={tabJobs}
                  filters={
                    activeTab === "applied" || activeTab === "saved"
                      ? { ...filters, role: "all" }
                      : filters
                  }
                  onApplied={handleApplied}
                  onSaved={handleSaved}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
