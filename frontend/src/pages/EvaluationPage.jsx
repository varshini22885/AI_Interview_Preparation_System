import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ScoreCard, TopBar } from "../App.jsx";
import { getEvaluations, getInterview } from "../api/interviews.js";
import { getReport } from "../api/reports.js";
import { EmptyState, ErrorBox, StatusLine } from "../components/StateViews.jsx";

export default function EvaluationPage() {
  const { interviewId } = useParams();

  const interviewQuery = useQuery({ queryKey: ["interview", interviewId], queryFn: () => getInterview(interviewId) });
  const evaluationsQuery = useQuery({
    queryKey: ["evaluations", interviewId],
    queryFn: () => getEvaluations(interviewId),
    refetchInterval: (query) => {
      const status = interviewQuery.data?.status;
      const active = status === "EVALUATING";
      return active && query.state.dataUpdateCount < 150 ? 2500 : false;
    },
  });
  const reportQuery = useQuery({
    queryKey: ["report", interviewId],
    queryFn: () => getReport(interviewId),
    retry: false,
  });

  const evaluations = evaluationsQuery.data ?? [];
  const latest = evaluations.length ? evaluations[evaluations.length - 1] : null;
  const report = reportQuery.data;
  const interviewStatus = interviewQuery.data?.status;

  return (
    <div className="app-page">
      <TopBar title="Answer Evaluation" />

      <div className="page-container">
        <div className="page-title">
          <span>06</span>
          <h1>Answer Evaluation</h1>
          <p>AI evaluation of your interview responses.</p>
        </div>

        {interviewQuery.isPending ? <StatusLine>Loading…</StatusLine> : null}
        <ErrorBox error={interviewQuery.error} onRetry={() => interviewQuery.refetch()} />
        <ErrorBox error={evaluationsQuery.error} onRetry={() => evaluationsQuery.refetch()} />

        {interviewStatus === "EVALUATING" ? (
          <StatusLine>Evaluating your answers — this page updates automatically.</StatusLine>
        ) : null}

        {report ? (
          <div className="score-main">
            <div className="score-circle">
              <strong>{report.overall_score}</strong>
              <small>/100</small>
            </div>
            <div>
              <span className="good-label">INTERVIEW COMPLETE</span>
              <h2>Final report available</h2>
            </div>
          </div>
        ) : null}

        {evaluations.length === 0 && interviewStatus !== "EVALUATING" ? (
          <EmptyState title="No evaluations yet">
            <p>Evaluations appear here after your answers are processed by the AI engine.</p>
          </EmptyState>
        ) : null}

        <div className="evaluation-grid">
          {latest ? (
            <>
              <ScoreCard
                title="Technical"
                score={`${latest.scores.technical_overall}/10`}
                scorePercent={latest.scores.technical_overall * 10}
              />
              <ScoreCard
                title="Communication"
                score={`${latest.scores.communication_overall}/10`}
                scorePercent={latest.scores.communication_overall * 10}
              />
              <ScoreCard title="Correctness" score={`${latest.scores.correctness}/10`} scorePercent={latest.scores.correctness * 10} />
              <ScoreCard title="Clarity" score={`${latest.scores.clarity}/10`} scorePercent={latest.scores.clarity * 10} />
            </>
          ) : null}
        </div>

        {evaluations.map((evaluation) => (
          <div key={evaluation.answer_id} className="feedback-box">
            <h2>{evaluation.question_text}</h2>
            <p>
              <strong>Strengths:</strong> {evaluation.detail?.strengths}
            </p>
            <p>
              <strong>Improve:</strong> {evaluation.detail?.improvements}
            </p>
            <p>
              <strong>Technical feedback:</strong> {evaluation.detail?.factual_feedback}
            </p>
            <p>
              <strong>Communication feedback:</strong> {evaluation.detail?.communication_feedback}
            </p>
            {evaluation.detail?.missing_concepts?.length ? (
              <p>
                <strong>Missing concepts:</strong> {evaluation.detail.missing_concepts.join(", ")}
              </p>
            ) : null}
          </div>
        ))}

        {report ? (
          <Link className="main-button center-button" to={`/report/${interviewId}`}>
            View Performance Report →
          </Link>
        ) : interviewStatus === "COMPLETED" || interviewStatus === "REPORT_GENERATING" ? (
          <Link className="main-button center-button" to={`/report/${interviewId}`}>
            Go to Report (generating…) →
          </Link>
        ) : null}
      </div>
    </div>
  );
}
