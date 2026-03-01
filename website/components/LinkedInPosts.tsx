"use client";

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

export default function LinkedInPosts({ posts }: Props) {
  if (posts.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <div className="text-5xl mb-4">📭</div>
        <p className="text-lg">No LinkedIn posts found yet.</p>
        <p className="text-sm mt-2">
          Run the scraper with LINKEDIN_EMAIL configured to fetch posts.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        {posts.length} posts — people posting job openings, reach-outs, and
        referrals on LinkedIn.
      </p>
      {posts.map((post) => {
        const days = Math.floor(
          (Date.now() - new Date(post.posted_date).getTime()) / 86400000
        );
        return (
          <div
            key={post.id}
            className="bg-slate-800 border border-slate-700 rounded-xl p-4 hover:border-slate-500 transition-colors"
          >
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
                <p className="text-xs text-slate-500 mt-0.5">
                  {post.author_headline}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span
                  className={`text-sm font-bold ${scoreColor(post.score)}`}
                >
                  {post.score}
                </span>
                <span className="text-xs text-slate-500">
                  {days === 0 ? "Today" : `${days}d ago`}
                </span>
                <a
                  href={post.post_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2 py-1 rounded-lg text-xs bg-blue-800 text-blue-300 hover:bg-blue-700 transition-colors"
                >
                  View Post →
                </a>
              </div>
            </div>

            {/* Tags */}
            <div className="flex flex-wrap gap-1.5 mt-2">
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
                className={`text-xs px-2 py-0.5 rounded-full ${
                  ROLE_COLORS[post.role_category] ||
                  "bg-slate-700 text-slate-300"
                }`}
              >
                {post.role_category.replace(/_/g, " ")}
              </span>
            </div>

            {/* Post text */}
            <p className="text-sm text-slate-300 mt-3 leading-relaxed line-clamp-5">
              {post.post_text}
            </p>

            {/* Contact info */}
            {(post.contact_email ||
              post.contact_linkedin ||
              post.contact_name) && (
              <div className="mt-3 pt-3 border-t border-slate-700 flex flex-wrap gap-3 text-xs">
                {post.contact_name && (
                  <span className="text-slate-400">
                    Contact:{" "}
                    <span className="text-slate-200">{post.contact_name}</span>
                  </span>
                )}
                {post.contact_email && (
                  <a
                    href={`mailto:${post.contact_email}`}
                    className="text-blue-400 hover:underline"
                  >
                    {post.contact_email}
                  </a>
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
            )}

            {/* Applied/Saved badges */}
            <div className="flex gap-2 mt-2">
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
  );
}
