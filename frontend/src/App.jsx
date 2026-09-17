import { useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import "./App.css";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import ResumePage from "./pages/ResumePage.jsx";
import SetupPage from "./pages/SetupPage.jsx";
import LobbyPage from "./pages/LobbyPage.jsx";
import InterviewPage from "./pages/InterviewPage.jsx";
import EvaluationPage from "./pages/EvaluationPage.jsx";
import FeedbackPage from "./pages/FeedbackPage.jsx";
import ReportPage from "./pages/ReportPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import ProtectedRoute from "./auth/ProtectedRoute.jsx";

function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route
          path="/resume"
          element={
            <ProtectedRoute>
              <ResumePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/setup"
          element={
            <ProtectedRoute>
              <SetupPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/lobby/:interviewId"
          element={
            <ProtectedRoute>
              <LobbyPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/interview/:interviewId"
          element={
            <ProtectedRoute>
              <InterviewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/evaluation/:interviewId"
          element={
            <ProtectedRoute>
              <EvaluationPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/feedback/:interviewId"
          element={
            <ProtectedRoute>
              <FeedbackPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/report/:interviewId"
          element={
            <ProtectedRoute>
              <ReportPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <HistoryPage />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </div>
  );
}

export default App;

/* ================= TOP BAR ================= */

export function TopBar({ title, dark = false }) {
  const navigate = useNavigate();
  return (
    <div className={`top-bar ${dark ? "top-dark" : ""}`}>
      <button type="button" onClick={() => navigate("/")}>
        ← Home
      </button>
      <strong>{title}</strong>
      <span>AI INTERVIEW PREPARATION SYSTEM</span>
    </div>
  );
}

/* ================= OPTION BOX ================= */

/**
 * Preserved original component; now optionally controlled so page state
 * (the interview configuration) lives in one place instead of per-box.
 */
export function OptionBox({ title, options, value, onChange }) {
  const [internal, setInternal] = useState(options[1]?.value ?? options[0]?.value);
  const selected = value !== undefined ? value : internal;
  const setOption = (next) => {
    if (onChange) onChange(next);
    else setInternal(next);
  };
  return (
    <div className="option-box">
      <h3>{title}</h3>
      <div>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={selected === option.value ? "selected" : ""}
            onClick={() => setOption(option.value)}
            aria-pressed={selected === option.value}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ================= SCORE CARD ================= */

export function ScoreCard({ title, score, scorePercent }) {
  // scorePercent must be derived from a REAL persisted score by the caller.
  const width = typeof scorePercent === "number" ? `${Math.max(0, Math.min(100, scorePercent))}%` : score;
  return (
    <div className="score-card">
      <span>{title}</span>
      <strong>{score}</strong>
      <div className="score-bar">
        <div style={{ width }}></div>
      </div>
    </div>
  );
}

/* ================= HISTORY CARD ================= */

export function HistoryCard({ date, role, type, score, onViewReport }) {
  const navigate = useNavigate();
  return (
    <div className="history-card">
      <div className="history-date">
        <small>DATE</small>
        <strong>{date}</strong>
      </div>
      <div>
        <small>ROLE</small>
        <strong>{role}</strong>
      </div>
      <div>
        <small>TYPE</small>
        <strong>{type}</strong>
      </div>
      <div className="history-score">
        <small>SCORE</small>
        <strong>{score}</strong>
      </div>
      <button type="button" onClick={() => (onViewReport ? onViewReport() : navigate("/history"))}>
        View Report →
      </button>
    </div>
  );
}
