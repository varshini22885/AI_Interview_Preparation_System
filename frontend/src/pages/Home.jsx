import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

const FEATURES = [
  { number: "01", title: "Resume & Role Analysis", text: "Upload your resume and select your target role.", to: "/resume" },
  { number: "02", title: "Dynamic Question Generation", text: "Generate personalized questions for your interview.", to: "/setup" },
  { number: "03", title: "Role-Based Prompting", text: "Get questions based on your selected job role.", to: "/setup" },
  { number: "04", title: "Conversational Interview", text: "Experience a realistic AI-powered interview.", to: "/history" },
  { number: "05", title: "Follow-up Questions", text: "AI generates intelligent follow-up questions.", to: "/history" },
  { number: "06", title: "Answer Evaluation", text: "Get AI-based evaluation of your answers.", to: "/history" },
  { number: "07", title: "Personalized Feedback", text: "Understand your strengths and areas to improve.", to: "/history" },
  { number: "08", title: "Performance Report", text: "View your complete interview performance.", to: "/history" },
  { number: "09", title: "Interview History", text: "Review your previous interview results.", to: "/history" },
];

function Home() {
  const navigate = useNavigate();
  const { user, status, logout } = useAuth();

  return (
    <div className="home-page">
      {/* NAVBAR */}

      <nav className="navbar">
        <div className="brand">
          <div className="brand-logo">AI</div>
          <strong>AI INTERVIEW PREPARATION SYSTEM</strong>
        </div>

        <div className="nav-links">
          <button type="button" onClick={() => navigate("/")}>
            Home
          </button>
          <button type="button" onClick={() => navigate(status === "authenticated" ? "/history" : "/login")}>
            History
          </button>
          {status === "authenticated" ? (
            <>
              <span className="nav-user">{user?.email}</span>
              <button type="button" onClick={() => logout()}>
                Log out
              </button>
            </>
          ) : (
            <button type="button" onClick={() => navigate("/login")}>
              Sign in
            </button>
          )}
        </div>
      </nav>

      {/* HERO */}

      <section className="hero-section">
        <div className="hero-content">
          <span className="hero-badge">✦ AI-POWERED INTERVIEW PLATFORM</span>
          <h1>
            AI INTERVIEW
            <br />
            <span>PREPARATION SYSTEM</span>
          </h1>
          <p>
            Practice smarter. Prepare better.
            <br />
            Perform better with AI-powered interviews.
          </p>
          <button
            className="main-button hero-button"
            type="button"
            onClick={() => navigate(status === "authenticated" ? "/resume" : "/register")}
          >
            Start Interview →
          </button>
        </div>
      </section>

      {/* FEATURES */}

      <section className="features-section">
        <div className="section-heading">
          <span>PLATFORM FEATURES</span>
          <h2>Everything you need to prepare.</h2>
        </div>

        <div className="features-grid">
          {FEATURES.map((feature) => (
            <button className="feature-card" key={feature.number} type="button" onClick={() => navigate(feature.to)}>
              <span className="feature-number">{feature.number}</span>
              <span className="feature-arrow">↗</span>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
              <span className="feature-open">Open →</span>
            </button>
          ))}
        </div>
      </section>

      {/* FOOTER */}

      <footer className="home-footer">
        <strong>AI INTERVIEW PREPARATION SYSTEM</strong>
        <span>AI-powered interview preparation</span>
      </footer>
    </div>
  );
}

export default Home;
