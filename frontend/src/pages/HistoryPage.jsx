import { useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { HistoryCard, TopBar } from "../App.jsx";
import { getHistory } from "../api/history.js";
import { EmptyState, ErrorBox, StatusLine } from "../components/StateViews.jsx";
import { DIFFICULTY_LABELS, INTERVIEW_TYPE_LABELS, formatDateTime } from "../lib/format.js";

const PAGE_SIZE = 10;

export default function HistoryPage({ pageSizeForTest = null }) {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [role, setRole] = useState("");
  const [interviewType, setInterviewType] = useState("");
  const [difficulty, setDifficulty] = useState("");

  // pageSizeForTest is a test-only seam (default production PAGE_SIZE).
  const pageSize = pageSizeForTest ?? PAGE_SIZE;
  const historyQuery = useQuery({
    queryKey: ["history", page, role, interviewType, difficulty, pageSize],
    queryFn: () => getHistory({ page, pageSize, role: role || undefined, interviewType: interviewType || undefined, difficulty: difficulty || undefined }),
    placeholderData: keepPreviousData,
  });

  const items = historyQuery.data?.items ?? [];
  const total = historyQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="app-page">
      <TopBar title="Interview History" />

      <div className="page-container">
        <div className="page-title">
          <span>09</span>
          <h1>Interview History</h1>
          <p>Review your previous interview performance.</p>
        </div>

        <div className="history-filters">
          <label htmlFor="filter-role">Role</label>
          <input
            id="filter-role"
            type="search"
            value={role}
            onChange={(e) => {
              setRole(e.target.value);
              setPage(1);
            }}
          />
          <label htmlFor="filter-type">Type</label>
          <select
            id="filter-type"
            value={interviewType}
            onChange={(e) => {
              setInterviewType(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All</option>
            {Object.entries(INTERVIEW_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <label htmlFor="filter-difficulty">Difficulty</label>
          <select
            id="filter-difficulty"
            value={difficulty}
            onChange={(e) => {
              setDifficulty(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All</option>
            {Object.entries(DIFFICULTY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {historyQuery.isPending ? <StatusLine>Loading history…</StatusLine> : null}
        <ErrorBox error={historyQuery.error} onRetry={() => historyQuery.refetch()} />

        {!historyQuery.isPending && !historyQuery.error && items.length === 0 ? (
          <EmptyState title="No interviews found">
            <p>Complete an interview and its report will appear here.</p>
            <button className="main-button" type="button" onClick={() => navigate("/setup")}>
              Create an Interview →
            </button>
          </EmptyState>
        ) : null}

        <div className="history-list">
          {items.map((item) => (
            <HistoryCard
              key={item.id}
              date={formatDateTime(item.completed_at)}
              role={item.target_role}
              type={INTERVIEW_TYPE_LABELS[item.interview_type] || item.interview_type}
              score={item.overall_score !== null && item.overall_score !== undefined ? `${item.overall_score}%` : "—"}
              onViewReport={() => navigate(`/report/${item.id}`)}
            />
          ))}
        </div>

        {totalPages > 1 ? (
          <div className="pagination" role="navigation" aria-label="History pages">
            <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              ← Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next →
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
