import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { TopBar } from "../App.jsx";
import { getReport } from "../api/reports.js";
import { EmptyState, ErrorBox, StatusLine } from "../components/StateViews.jsx";

function FeedbackLines({ text }) {
  if (!text) return null;
  const lines = String(text)
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length <= 1) return <p>{text}</p>;
  return (
    <ul>
      {lines.map((line, index) => (
        <li key={index}>{line}</li>
      ))}
    </ul>
  );
}

export default function FeedbackPage() {
  const { interviewId } = useParams();
  const reportQuery = useQuery({
    queryKey: ["report", interviewId],
    queryFn: () => getReport(interviewId),
    retry: false,
    refetchInterval: (query) => (query.state.data ? false : 2500),
  });

  const report = reportQuery.data;

  return (
    <div className="app-page">
      <TopBar title="Personalized Feedback" />

      <div className="page-container">
        <div className="page-title">
          <span>07</span>
          <h1>Personalized Feedback</h1>
          <p>Improve your interview performance with AI insights.</p>
        </div>

        {reportQuery.isPending ? <StatusLine>Loading feedback…</StatusLine> : null}

        {reportQuery.error ? (
          reportQuery.error.status === 409 ? (
            <StatusLine>Feedback is being prepared. This page updates automatically.</StatusLine>
          ) : (
            <ErrorBox error={reportQuery.error} onRetry={() => reportQuery.refetch()} />
          )
        ) : null}

        {report ? (
          <div className="feedback-grid">
            <div className="feedback-box">
              <div className="feedback-icon">✓</div>
              <h2>Strengths</h2>
              {report.strengths ? (
                <FeedbackLines text={report.strengths} />
              ) : (
                <EmptyState title="No strengths recorded yet" />
              )}
            </div>

            <div className="feedback-box">
              <div className="feedback-icon">!</div>
              <h2>Improve</h2>
              {report.areas_for_improvement ? (
                <FeedbackLines text={report.areas_for_improvement} />
              ) : (
                <EmptyState title="No improvement notes yet" />
              )}
            </div>
          </div>
        ) : null}

        {report ? (
          <Link className="main-button center-button" to={`/report/${interviewId}`}>
            View Performance Report →
          </Link>
        ) : null}
      </div>
    </div>
  );
}
