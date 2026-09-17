import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { TopBar } from "../App.jsx";
import {
  finishInterview,
  getCurrentQuestion,
  getInterview,
  getTranscript,
  pauseInterview,
  submitAnswer,
} from "../api/interviews.js";
import { ErrorBox, StatusLine } from "../components/StateViews.jsx";
import { formatElapsed, newIdempotencyKey, pad2 } from "../lib/format.js";

const ACTIVE_POLL_INTERVAL_MS = 2000;

/** Whether the current live question already appears in the transcript,
 *  so we don't render it twice. Presentation-only helper. */
function transcriptItemForCurrent(transcript, questionId) {
  if (!transcript || !questionId) return false;
  return transcript.some((item) => String(item.question_id) === String(questionId));
}

/** Idempotency key ref: one key per LOGICAL submission. Retrying the same
 * answer (network failure, double click) reuses the SAME key; starting a
 * new answer generates a new one. Keys are never logged. */
function useIdempotencyKey() {
  const keyRef = useRef(null);
  const reset = useCallback(() => {
    keyRef.current = null;
  }, []);
  const next = useCallback(() => {
    if (!keyRef.current) keyRef.current = newIdempotencyKey();
    return keyRef.current;
  }, []);
  return { current: keyRef.current, next, reset };
}

/** Presentation-only elapsed time derived from the server's started_at. */
function useElapsedTicker(startedAt) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!startedAt) return undefined;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [startedAt]);
  return formatElapsed(startedAt, now);
}

export default function InterviewPage() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

    const [draft, setDraft] = useState("");
  const idempotency = useIdempotencyKey();
  const [actionError, setActionError] = useState(null);
  const [notice, setNotice] = useState(null);

  const interviewQuery = useQuery({ queryKey: ["interview", interviewId], queryFn: () => getInterview(interviewId) });
  const transcriptQuery = useQuery({
    queryKey: ["transcript", interviewId],
    queryFn: () => getTranscript(interviewId),
  });

  const currentQuery = useQuery({
    queryKey: ["current", interviewId],
    queryFn: () => getCurrentQuestion(interviewId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      const active = status === "EVALUATING" || status === "NEXT_QUESTION";
      return active && query.state.dataUpdateCount < 150 ? ACTIVE_POLL_INTERVAL_MS : false;
    },
  });

  const current = currentQuery.data;
  const status = current?.status ?? interviewQuery.data?.status;
  const answerAllowed = Boolean(current?.answer_allowed);
  // During FOLLOW_UP_REQUIRED the authoritative follow-up text is the question;
  // its parent question id (current.question_id) is what submit_answer expects.
  const followUp = current?.follow_up ?? null;
  const elapsed = useElapsedTicker(interviewQuery.data?.started_at);

  const submitMutation = useMutation({
    mutationFn: ({ questionId, text, key }) =>
      submitAnswer(interviewId, { questionId, answerText: text, idempotencyKey: key }),
        onSuccess: () => {
      idempotency.reset();
      setDraft("");
      queryClient.invalidateQueries({ queryKey: ["current", interviewId] });
      queryClient.invalidateQueries({ queryKey: ["transcript", interviewId] });
      queryClient.invalidateQueries({ queryKey: ["interview", interviewId] });
    },
  });

  const finishMutation = useMutation({
    mutationFn: () => finishInterview(interviewId),
    onSuccess: (interview) => {
      queryClient.invalidateQueries({ queryKey: ["interview", interviewId] });
      if (interview?.status === "COMPLETED") navigate(`/report/${interviewId}`);
    },
  });

  async function onPause() {
    setActionError(null);
    setNotice(null);
    try {
      await pauseInterview(interviewId);
    } catch (err) {
      // The backend has no PAUSED state by design; surface its message.
      setNotice(err.message || "Pause is not currently available for this interview.");
    }
  }

  function onSubmitAnswer(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !current?.question_id || submitMutation.isPending) return;
    setActionError(null);
    const key = idempotency.next();
    submitMutation.mutate({ questionId: current.question_id, text, key });
  }

  if (interviewQuery.isPending || interviewQuery.error) {
    return (
      <div className="app-page">
        <TopBar title="Interview" />
        <div className="page-container">
          <StatusLine>{interviewQuery.isPending ? "Loading interview…" : ""}</StatusLine>
          <ErrorBox error={interviewQuery.error} onRetry={() => interviewQuery.refetch()} />
        </div>
      </div>
    );
  }

  const finished = ["COMPLETED", "REPORT_GENERATING", "REPORT_READY"].includes(status);
  if (status === "FAILED") {
    return (
      <div className="app-page">
        <TopBar title="Interview" />
        <div className="page-container">
          <h1>This interview failed.</h1>
          <p>Please create a new interview from the setup page.</p>
          <button className="main-button" type="button" onClick={() => navigate("/setup")}>
            Back to Setup
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="interview-page">
      <div className="interview-top">
        <strong>AI INTERVIEW PREPARATION SYSTEM</strong>

        <div className="question-progress">
          QUESTION {pad2((current?.order_index ?? 0) + 1)} /{" "}
          {pad2(current?.total_questions ?? interviewQuery.data?.total_questions ?? 0)}
          <div>
            <span
              style={{
                width: `${Math.min(100, (((current?.order_index ?? 0) + 1) / Math.max(1, current?.total_questions ?? 1)) * 100)}%`,
              }}
            ></span>
          </div>
        </div>

        <div className="timer" aria-label="Elapsed time, derived from the server start time">
          {elapsed ?? "--:--"}
        </div>
      </div>

            <div className="conversation-container">
        {transcriptQuery.isPending && !current ? (
          <StatusLine>Loading conversation…</StatusLine>
        ) : null}
        <ErrorBox error={transcriptQuery.error} onRetry={() => transcriptQuery.refetch()} />

        {(transcriptQuery.data ?? []).map((item) => (
          <div key={item.question_id}>
            <ChatRow role="ai" label={item.question_type === "BEHAVIORAL" ? "BEHAVIORAL QUESTION" : "TECHNICAL QUESTION"}>
              {item.question_text}
            </ChatRow>
            {item.follow_ups.map((followUp) => (
              <ChatRow key={`${item.question_id}-${followUp.created_at}`} role="ai" label="AI FOLLOW-UP">
                {followUp.follow_up_text}
              </ChatRow>
            ))}
            {item.answers.map((answer) => (
              <ChatRow key={answer.answer_id} role="user" label={`YOUR ANSWER (ATTEMPT ${answer.attempt_number})`}>
                {answer.answer_text}
              </ChatRow>
            ))}
          </div>
        ))}

        {current &&
          !transcriptItemForCurrent(transcriptQuery.data, current.question_id) && (
            <ChatRow
              role="ai"
              label={current.question_type === "BEHAVIORAL" ? "BEHAVIORAL QUESTION" : "TECHNICAL QUESTION"}
            >
              {current.question_text}
            </ChatRow>
          )}

        {status === "EVALUATING" ? (
          <p className="status-line" role="status" aria-live="polite">
            Evaluating your answer…
          </p>
        ) : null}

        {status === "NEXT_QUESTION" ? (
          <p className="status-line" role="status" aria-live="polite">
            Preparing the next question…
          </p>
        ) : null}

                {status === "FOLLOW_UP_REQUIRED" && followUp ? (
          <ChatRow role="ai" label="AI FOLLOW-UP">
            {followUp.follow_up_text}
          </ChatRow>
        ) : null}

        {finished ? (
          <p className="status-line" role="status" aria-live="polite">
            Interview complete. Your final report is being generated.
          </p>
        ) : null}

        {currentQuery.error ? <ErrorBox error={currentQuery.error} onRetry={() => currentQuery.refetch()} /> : null}
        <ErrorBox error={submitMutation.error} />
        <ErrorBox error={actionError} />
        {notice ? (
          <p className="status-line" role="status">
            {notice}
          </p>
        ) : null}

        {answerAllowed && current && !finished ? (
          <form className="answer-area" onSubmit={onSubmitAnswer}>
            <label htmlFor="answer-text" className="sr-only">
              Your answer
            </label>
            <textarea
              id="answer-text"
              placeholder={status === "FOLLOW_UP_REQUIRED" ? "Continue your answer..." : "Type your answer here..."}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={submitMutation.isPending}
            />
            <div className="answer-actions">
              <span>
                {status === "FOLLOW_UP_REQUIRED" ? "Follow-up question from your AI interviewer" : "AI is listening..."}
              </span>
              <button className="main-button" type="submit" disabled={submitMutation.isPending || !draft.trim()}>
                {submitMutation.isPending ? "Submitting…" : "Send Answer →"}
              </button>
            </div>
          </form>
        ) : null}
      </div>

      <div className="interview-controls">
        <button type="button" className="retry-button" onClick={onPause}>
          Pause
        </button>
        <button
          type="button"
          className="retry-button"
          disabled={finishMutation.isPending}
          onClick={() => {
            if (window.confirm("Finish the interview now and get your report?")) {
              finishMutation.mutate();
            }
          }}
        >
          {finishMutation.isPending ? "Finishing…" : "Finish Interview"}
        </button>
      </div>
    </div>
  );
}

function ChatRow({ role, label, children }) {
  if (role === "user") {
    return (
      <div className="chat-row user-row">
        <div className="chat-message user-message">
          <span className="message-label">{label}</span>
          <p>{children}</p>
        </div>
        <div className="chat-avatar user-avatar">YOU</div>
      </div>
    );
  }
  return (
    <div className="chat-row ai-row">
      <div className="chat-avatar">AI</div>
      <div className="chat-message ai-message">
        <span className="message-label">{label}</span>
        <p className="main-question">{children}</p>
      </div>
    </div>
  );
}
