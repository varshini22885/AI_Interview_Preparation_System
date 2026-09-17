import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ScoreCard, TopBar } from "../App.jsx";
import { getReport } from "../api/reports.js";
import { ErrorBox, StatusLine } from "../components/StateViews.jsx";
import { scoreBandLabel } from "../lib/format.js";

export default function ReportPage() {
  const { interviewId } = useParams();

  const reportQuery = useQuery({
    queryKey: ["report", interviewId],
    queryFn: () => getReport(interviewId),
    retry: false,
    // Poll only while no persisted report exists yet (COMPLETED ->
    // REPORT_GENERATING -> REPORT_READY); stop as soon as it arrives.
    refetchInterval: (query) => (query.state.data ? false : 2500),
  });

  const report = reportQuery.data;

  return (
    <div className="app-page">
      <TopBar title="Performance Report" />

      <div className="page-container">
        <div className="page-title">
          <span>08</span>
          <h1>Interview Performance</h1>
          <p>Your complete interview performance report.</p>
        </div>

        {reportQuery.isPending ? <StatusLine>Loading report…</StatusLine> : null}

        {reportQuery.error ? (
          reportQuery.error.status === 409 ? (
            <StatusLine role="status" aria-live="polite">
              {reportQuery.error.message} — this page updates automatically.
            </StatusLine>
          ) : (
            <ErrorBox error={reportQuery.error} onRetry={() => reportQuery.refetch()} />
          )
        ) : null}

        {report ? (
          <>
            <div className="final-score">
              <div className="score-circle big">
                <strong>{report.overall_score}</strong>
                <small>/100</small>
              </div>
              <div>
                <span className="good-label">INTERVIEW COMPLETE</span>
                <h2>{scoreBandLabel(report.overall_score)}</h2>
                <p>
                  Based on {report.total_questions_answered} evaluated answer
                  {report.total_questions_answered === 1 ? "" : "s"}.
                </p>
              </div>
            </div>

            <div className="report-grid">
              <ScoreCard title="Technical" score={`${report.technical_score}%`} scorePercent={report.technical_score} />
              <ScoreCard
                title="Communication"
                score={`${report.communication_score}%`}
                scorePercent={report.communication_score}
              />
              <ScoreCard title="Overall" score={`${report.overall_score}%`} scorePercent={report.overall_score} />
              <ScoreCard
                title="Answered"
                score={String(report.total_questions_answered)}
                scorePercent={Math.min(100, report.total_questions_answered * 10)}
              />
            </div>
          </>
        ) : null}

        <div className="report-actions">
          <Link className="main-button center-button" to={`/feedback/${interviewId}`}>
            View Detailed Feedback →
          </Link>
          <Link className="main-button center-button" to="/history">
            Save & View History →
          </Link>
        </div>
      </div>
    </div>
  );
}
