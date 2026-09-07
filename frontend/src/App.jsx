import { useState } from "react";
import Home from "./pages/Home";
import "./App.css";

function App() {
  const [page, setPage] = useState("home");

  const goHome = () => {
    setPage("home");
  };

  return (
    <div className="app">

      {/* ================= HOME ================= */}

      {page === "home" && (
        <Home setPage={setPage} />
      )}


      {/* ================= RESUME ================= */}

      {page === "resume" && (
        <div className="app-page">

          <TopBar
            setPage={setPage}
            title="Resume Analysis"
          />

          <div className="page-container">

            <div className="page-title">

              <span>01</span>

              <h1>
                Resume & Role Analysis
              </h1>

              <p>
                Upload your resume and define your target role.
              </p>

            </div>


            <div className="resume-layout">

              <div className="resume-upload-card">

                <div className="upload-icon">
                  ↑
                </div>

                <h2>
                  Upload Resume
                </h2>

                <p>
                  PDF, DOC or DOCX
                </p>

                <input
                  type="file"
                  id="resume"
                  accept=".pdf,.doc,.docx"
                />

                <label
                  htmlFor="resume"
                  className="upload-button"
                >
                  Choose Resume
                </label>

              </div>


              <div className="form-card">

                <label>
                  Target Job Role
                </label>

                <select>

                  <option>
                    Software Developer
                  </option>

                  <option>
                    Frontend Developer
                  </option>

                  <option>
                    Backend Developer
                  </option>

                  <option>
                    Full Stack Developer
                  </option>

                  <option>
                    Data Analyst
                  </option>

                  <option>
                    Machine Learning Engineer
                  </option>

                </select>


                <label>
                  Programming Language
                </label>

                <select>

                  <option>
                    Python
                  </option>

                  <option>
                    Java
                  </option>

                  <option>
                    JavaScript
                  </option>

                  <option>
                    C++
                  </option>

                </select>


                <button
                  className="main-button"
                  onClick={() => setPage("setup")}
                >
                  Continue →
                </button>

              </div>

            </div>

          </div>

        </div>
      )}


      {/* ================= SETUP ================= */}

      {page === "setup" && (
        <div className="app-page">

          <TopBar
            setPage={setPage}
            title="Interview Setup"
          />

          <div className="page-container">

            <div className="page-title">

              <span>02</span>

              <h1>
                Interview Setup
              </h1>

              <p>
                Configure your personalized interview.
              </p>

            </div>


            <div className="setup-grid">

              <OptionBox
                title="Difficulty"
                options={[
                  "Easy",
                  "Medium",
                  "Hard",
                  "Expert",
                ]}
              />

              <OptionBox
                title="Interview Type"
                options={[
                  "Technical",
                  "Behavioral",
                  "Mixed",
                ]}
              />

              <OptionBox
                title="Interviewer Persona"
                options={[
                  "Friendly",
                  "Professional",
                  "Strict",
                ]}
              />

              <OptionBox
                title="Questions"
                options={[
                  "5",
                  "10",
                  "15",
                  "20",
                ]}
              />

            </div>


            <button
              className="main-button center-button"
              onClick={() => setPage("lobby")}
            >
              Start Interview →
            </button>

          </div>

        </div>
      )}


      {/* ================= LOBBY ================= */}

      {page === "lobby" && (
        <div className="app-page dark-page">

          <TopBar
            setPage={setPage}
            title="Interview Lobby"
            dark
          />

          <div className="lobby">

            <div className="ai-avatar">
              AI
            </div>

            <span className="live-label">
              ● AI INTERVIEWER READY
            </span>

            <h1>
              Ready for your interview?
            </h1>

            <p>
              Your personalized interview is ready to begin.
            </p>


            <div className="lobby-details">

              <div>
                <small>ROLE</small>
                <strong>Software Developer</strong>
              </div>

              <div>
                <small>DIFFICULTY</small>
                <strong>Medium</strong>
              </div>

              <div>
                <small>QUESTIONS</small>
                <strong>10</strong>
              </div>

            </div>


            <button
              className="main-button"
              onClick={() => setPage("interview")}
            >
              Enter Interview →
            </button>

          </div>

        </div>
      )}


      {/* ================= CONVERSATIONAL INTERVIEW ================= */}

      {page === "interview" && (
        <div className="interview-page">

          <div className="interview-top">

            <strong>
              AI INTERVIEW PREPARATION SYSTEM
            </strong>


            <div className="question-progress">

              QUESTION 01 / 10

              <div>
                <span></span>
              </div>

            </div>


            <div className="timer">
              29:42
            </div>

          </div>


          <div className="conversation-container">


            {/* AI GREETING */}

            <div className="chat-row ai-row">

              <div className="chat-avatar">
                AI
              </div>

              <div className="chat-message ai-message">

                <span className="message-label">
                  AI INTERVIEWER
                </span>

                <p>
                  Hi! Welcome to your AI interview.
                  Let's begin with a simple technical question.
                </p>

              </div>

            </div>


            {/* AI QUESTION */}

            <div className="chat-row ai-row">

              <div className="chat-avatar">
                AI
              </div>

              <div className="chat-message ai-message">

                <span className="message-label">
                  TECHNICAL QUESTION
                </span>

                <p className="main-question">
                  What is the difference between
                  a list and a tuple in Python?
                </p>

              </div>

            </div>


            {/* ANSWER AREA */}

            <div className="answer-area">

              <textarea
                placeholder="Type your answer here..."
              />

              <div className="answer-actions">

                <span>
                  AI is listening...
                </span>

                <button
                  className="main-button"
                  onClick={() => setPage("followup")}
                >
                  Send Answer →
                </button>

              </div>

            </div>

          </div>

        </div>
      )}


      {/* ================= FOLLOW UP ================= */}

      {page === "followup" && (
        <div className="interview-page">

          <div className="interview-top">

            <strong>
              AI INTERVIEW PREPARATION SYSTEM
            </strong>

            <div className="question-progress">

              QUESTION 02 / 10

              <div>
                <span
                  style={{
                    width: "20%",
                  }}
                ></span>
              </div>

            </div>

            <div className="timer">
              27:58
            </div>

          </div>


          <div className="conversation-container">


            {/* USER PREVIOUS ANSWER */}

            <div className="chat-row user-row">

              <div className="chat-message user-message">

                <span className="message-label">
                  YOUR ANSWER
                </span>

                <p>
                  A list is mutable, whereas a tuple
                  is immutable in Python.
                </p>

              </div>

              <div className="chat-avatar user-avatar">
                YOU
              </div>

            </div>


            {/* AI FOLLOW UP */}

            <div className="chat-row ai-row">

              <div className="chat-avatar">
                AI
              </div>

              <div className="chat-message ai-message">

                <span className="message-label">
                  AI FOLLOW-UP
                </span>

                <p className="main-question">
                  Good answer! Can you explain when
                  you would choose a tuple instead of a list?
                </p>

              </div>

            </div>


            {/* ANSWER */}

            <div className="answer-area">

              <textarea
                placeholder="Continue your answer..."
              />

              <div className="answer-actions">

                <span>
                  Follow-up question generated by AI
                </span>

                <button
                  className="main-button"
                  onClick={() => setPage("evaluation")}
                >
                  Submit Answer →
                </button>

              </div>

            </div>

          </div>

        </div>
      )}


      {/* ================= EVALUATION ================= */}

      {page === "evaluation" && (
        <div className="app-page">

          <TopBar
            setPage={setPage}
            title="Answer Evaluation"
          />

          <div className="page-container">

            <div className="page-title">

              <span>06</span>

              <h1>
                Answer Evaluation
              </h1>

              <p>
                AI evaluation of your interview response.
              </p>

            </div>


            <div className="score-main">

              <div className="score-circle">

                <strong>
                  82
                </strong>

                <small>
                  /100
                </small>

              </div>


              <div>

                <span className="good-label">
                  GOOD ANSWER
                </span>

                <h2>
                  Strong technical understanding
                </h2>

              </div>

            </div>


            <div className="evaluation-grid">

              <ScoreCard
                title="Correctness"
                score="88%"
              />

              <ScoreCard
                title="Clarity"
                score="80%"
              />

              <ScoreCard
                title="Communication"
                score="76%"
              />

              <ScoreCard
                title="Relevance"
                score="85%"
              />

            </div>


            <button
              className="main-button center-button"
              onClick={() => setPage("feedback")}
            >
              View Feedback →
            </button>

          </div>

        </div>
      )}


      {/* ================= FEEDBACK ================= */}

      {page === "feedback" && (
        <div className="app-page">

          <TopBar
            setPage={setPage}
            title="Personalized Feedback"
          />

          <div className="page-container">

            <div className="page-title">

              <span>07</span>

              <h1>
                Personalized Feedback
              </h1>

              <p>
                Improve your interview performance with AI insights.
              </p>

            </div>


            <div className="feedback-grid">

              <div className="feedback-box">

                <div className="feedback-icon">
                  ✓
                </div>

                <h2>
                  Strengths
                </h2>

                <p>
                  Good technical knowledge
                </p>

                <p>
                  Clear explanation
                </p>

                <p>
                  Relevant examples
                </p>

              </div>


              <div className="feedback-box">

                <div className="feedback-icon">
                  !
                </div>

                <h2>
                  Improve
                </h2>

                <p>
                  Use more structured answers
                </p>

                <p>
                  Improve communication flow
                </p>

                <p>
                  Add practical examples
                </p>

              </div>

            </div>


            <button
              className="main-button center-button"
              onClick={() => setPage("report")}
            >
              View Performance Report →
            </button>

          </div>

        </div>
      )}


      {/* ================= REPORT ================= */}

      {page === "report" && (
        <div className="app-page">

          <TopBar
            setPage={setPage}
            title="Performance Report"
          />

          <div className="page-container">

            <div className="page-title">

              <span>08</span>

              <h1>
                Interview Performance
              </h1>

              <p>
                Your complete interview performance report.
              </p>

            </div>


            <div className="final-score">

              <div className="score-circle big">

                <strong>
                  84
                </strong>

                <small>
                  /100
                </small>

              </div>


              <div>

                <span className="good-label">
                  INTERVIEW COMPLETE
                </span>

                <h2>
                  Great performance!
                </h2>

                <p>
                  You're ready to improve and perform even better.
                </p>

              </div>

            </div>


            <div className="report-grid">

              <ScoreCard
                title="Technical"
                score="87%"
              />

              <ScoreCard
                title="Communication"
                score="81%"
              />

              <ScoreCard
                title="Problem Solving"
                score="84%"
              />

              <ScoreCard
                title="Confidence"
                score="82%"
              />

            </div>


            <button
              className="main-button center-button"
              onClick={() => setPage("history")}
            >
              Save & View History →
            </button>

          </div>

        </div>
      )}


      {/* ================= HISTORY ================= */}

      {page === "history" && (
        <div className="app-page">

          <TopBar
            setPage={setPage}
            title="Interview History"
          />

          <div className="page-container">

            <div className="page-title">

              <span>09</span>

              <h1>
                Interview History
              </h1>

              <p>
                Review your previous interview performance.
              </p>

            </div>


            <div className="history-list">

              <HistoryCard
                date="September 06, 2026"
                role="Software Developer"
                type="Technical"
                score="84%"
              />

              <HistoryCard
                date="September 04, 2026"
                role="Frontend Developer"
                type="Mixed"
                score="78%"
              />

              <HistoryCard
                date="September 01, 2026"
                role="Data Analyst"
                type="Technical"
                score="88%"
              />

            </div>


            <button
              className="main-button center-button"
              onClick={goHome}
            >
              Back to Home
            </button>

          </div>

        </div>
      )}

    </div>
  );
}


/* ================= TOP BAR ================= */

function TopBar({
  setPage,
  title,
  dark = false,
}) {
  return (
    <div
      className={`top-bar ${
        dark ? "top-dark" : ""
      }`}
    >

      <button
        onClick={() => setPage("home")}
      >
        ← Home
      </button>

      <strong>
        {title}
      </strong>

      <span>
        AI INTERVIEW PREPARATION SYSTEM
      </span>

    </div>
  );
}


/* ================= OPTION BOX ================= */

function OptionBox({
  title,
  options,
}) {
  const [selected, setSelected] =
    useState(options[1]);

  return (
    <div className="option-box">

      <h3>
        {title}
      </h3>

      <div>

        {options.map((option) => (

          <button
            key={option}
            className={
              selected === option
                ? "selected"
                : ""
            }
            onClick={() =>
              setSelected(option)
            }
          >
            {option}
          </button>

        ))}

      </div>

    </div>
  );
}


/* ================= SCORE CARD ================= */

function ScoreCard({
  title,
  score,
}) {
  return (
    <div className="score-card">

      <span>
        {title}
      </span>

      <strong>
        {score}
      </strong>

      <div className="score-bar">

        <div
          style={{
            width: score,
          }}
        ></div>

      </div>

    </div>
  );
}


/* ================= HISTORY CARD ================= */

function HistoryCard({
  date,
  role,
  type,
  score,
}) {
  return (
    <div className="history-card">

      <div className="history-date">

        <small>
          DATE
        </small>

        <strong>
          {date}
        </strong>

      </div>


      <div>

        <small>
          ROLE
        </small>

        <strong>
          {role}
        </strong>

      </div>


      <div>

        <small>
          TYPE
        </small>

        <strong>
          {type}
        </strong>

      </div>


      <div className="history-score">

        <small>
          SCORE
        </small>

        <strong>
          {score}
        </strong>

      </div>


      <button>
        View Report →
      </button>

    </div>
  );
}


export default App;