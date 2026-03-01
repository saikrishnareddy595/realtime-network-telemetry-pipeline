"use client";

import { useState } from "react";
import { LinkedInPost } from "@/lib/types";

interface Props {
  posts: LinkedInPost[];
}

function scoreColor(score: number): string {
  if (score >= 80) return "text-green-400";
  if (score >= 60) return "text-yellow-400";
  return "text-slate-400";
}

const ROLE_COLORS: Record<string, string> = {
  data_engineer: "bg-blue-900 text-blue-300",
  ai_engineer: "bg-violet-900 text-violet-300",
  ml_engineer: "bg-indigo-900 text-indigo-300",
  nlp_engineer: "bg-teal-900 text-teal-300",
  cv_engineer: "bg-cyan-900 text-cyan-300",
  data_scientist: "bg-pink-900 text-pink-300",
  other: "bg-slate-700 text-slate-300",
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="ml-1 text-xs px-1.5 py-0.5 rounded bg-slate-600 hover:bg-slate-500 text-slate-300 transition-colors"
      title="Copy email"
    >
      {copied ? "✓" : "Copy"}
    </button>
  );
}

export default function LinkedInPosts({ posts }: Props) {
  // Filter controls
  const [emailOnly, setEmailOnly] = useState(false);
  const [minScore, setMinScore] = useState(0);
  const [search, setSearch] = useState("");

  const filtered = posts.filter((p) => {
    if (emailOnly && !p.contact_email) return false;
    if (p.score < minScore) return false;
    if (search) {
      const q = search.toLowerCase();
      const hay = `${p.author_name} ${p.extracted_title} ${p.extracted_company} ${p.post_text}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  const withEmail = posts.filter((p) => p.contact_email).length;

  if (posts.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <div className="text-5xl mb-4">📭</div>
        <p className="text-lg">No LinkedIn recruiter posts found yet.</p>
        <p className="text-sm mt-2">
          Run the scraper with LINKEDIN_EMAIL configured to fetch posts.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3 bg-slate-800 border border-slate-700 rounded-xl p-4">
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search recruiter, title, company…"
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
        <label className="flex items-center gap-2 cursor-pointer whitespace-nowrap">
          <input
            type="checkbox"
            checked={emailOnly}
            onChange={(e) => setEmailOnly(e.target.checked)}
            className="accent-orange-400"
          />
          <span className="text-sm text-slate-300">
            Email only
            {withEmail > 0 && (
              <span className="ml-1 bg-orange-600 text-white text-xs px-1.5 py-0.5 rounded-full">
                {withEmail}
              </span>
            )}
          </span>
        </label>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 whitespace-nowrap">Min score: {minScore}</span>
          <input
            type="range"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-24 accent-blue-500"
          />
        </div>
        <span className="text-xs text-slate-500">
          Showing {filtered.length} / {posts.length}
        </span>
      </div>

      {/* Posts grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((post) => {
          const days = Math.floor(
            (Date.now() - new Date(post.posted_date).getTime()) / 86400000
          );
          return (
            <div
              key={post.id}
              className={`bg-slate-800 border rounded-xl p-4 hover:border-slate-500 transition-colors flex flex-col gap-2 ${post.contact_email ? "border-orange-700/60" : "border-slate-700"
                }`}
            >
              {/* Email badge at top if present */}
              {post.contact_email && (
                <div className="flex items-center gap-1 bg-orange-900/40 border border-orange-700/50 rounded-lg px-2 py-1.5">
                  <span className="text-orange-400 text-xs font-semibold">📧 Recruiter Email:</span>
                  <a
                    href={`mailto:${post.contact_email}`}
                    className="text-orange-300 text-xs font-mono hover:underline truncate"
                  >
                    {post.contact_email}
                  </a>
                  <CopyButton text={post.contact_email} />
                </div>
              )}

              {/* Author */}
              <div className="flex items-start justify-between gap-3">
                <div>
                  <a
                    href={post.author_profile_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-blue-400 hover:underline text-sm"
                  >
                    {post.author_name}
                  </a>
                  <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                    {post.author_headline}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-sm font-bold ${scoreColor(post.score)}`}>
                    {post.score}
                  </span>
                  <span className="text-xs text-slate-500">
                    {days === 0 ? "Today" : `${days}d ago`}
                  </span>
                  <a
                    href={post.post_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2 py-1 rounded-lg text-xs bg-blue-800 text-blue-300 hover:bg-blue-700 transition-colors whitespace-nowrap"
                  >
                    View →
                  </a>
                </div>
              </div>

              {/* Tags */}
              <div className="flex flex-wrap gap-1.5">
                {post.extracted_title && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-200">
                    {post.extracted_title}
                  </span>
                )}
                {post.extracted_company && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-400">
                    {post.extracted_company}
                  </span>
                )}
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${ROLE_COLORS[post.role_category] || "bg-slate-700 text-slate-300"
                    }`}
                >
                  {post.role_category.replace(/_/g, " ")}
                </span>
              </div>

              {/* Post text */}
              <p className="text-sm text-slate-300 leading-relaxed line-clamp-4 flex-1">
                {post.post_text}
              </p>

              {/* Contact info row */}
              <div className="flex flex-wrap gap-2 text-xs pt-1">
                {post.contact_name && post.contact_name !== post.author_name && (
                  <span className="text-slate-400">
                    Contact: <span className="text-slate-200">{post.contact_name}</span>
                  </span>
                )}
                {post.contact_linkedin && (
                  <a
                    href={post.contact_linkedin}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:underline"
                  >
                    LinkedIn Profile →
                  </a>
                )}
              </div>

              {/* Applied/Saved badges */}
              <div className="flex gap-2">
                {post.applied && (
                  <span className="text-xs bg-blue-900 text-blue-300 px-2 py-0.5 rounded-full">
                    Applied ✓
                  </span>
                )}
                {post.saved && (
                  <span className="text-xs bg-pink-900 text-pink-300 px-2 py-0.5 rounded-full">
                    Saved ★
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          No posts match your filters.
        </div>
      )}
    </div>
  );
}
