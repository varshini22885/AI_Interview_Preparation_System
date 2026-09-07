function Home({ setPage }) {
  const features = [
    {
      number: "01",
      title: "Resume & Role Analysis",
      text: "Upload your resume and select your target role.",
      page: "resume",
    },
    {
      number: "02",
      title: "Dynamic Question Generation",
      text: "Generate personalized questions for your interview.",
      page: "setup",
    },
    {
      number: "03",
      title: "Role-Based Prompting",
      text: "Get questions based on your selected job role.",
      page: "setup",
    },
    {
      number: "04",
      title: "Conversational Interview",
      text: "Experience a realistic AI-powered interview.",
      page: "lobby",
    },
    {
      number: "05",
      title: "Follow-up Questions",
      text: "AI generates intelligent follow-up questions.",
      page: "followup",
    },
    {
      number: "06",
      title: "Answer Evaluation",
      text: "Get AI-based evaluation of your answers.",
      page: "evaluation",
    },
    {
      number: "07",
      title: "Personalized Feedback",
      text: "Understand your strengths and areas to improve.",
      page: "feedback",
    },
    {
      number: "08",
      title: "Performance Report",
      text: "View your complete interview performance.",
      page: "report",
    },
    {
      number: "09",
      title: "Interview History",
      text: "Review your previous interview results.",
      page: "history",
    },
  ];

  return (
    <div className="home-page">

      {/* NAVBAR */}

      <nav className="navbar">

        <div className="brand">

          <div className="brand-logo">
            AI
          </div>

          <strong>
            AI INTERVIEW PREPARATION SYSTEM
          </strong>

        </div>

        <div className="nav-links">

          <button
            onClick={() => setPage("home")}
          >
            Home
          </button>

          <button
            onClick={() => setPage("history")}
          >
            History
          </button>

        </div>

      </nav>


      {/* HERO */}

      <section className="hero-section">

        <div className="hero-content">

          <span className="hero-badge">
            ✦ AI-POWERED INTERVIEW PLATFORM
          </span>

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
            onClick={() => setPage("resume")}
          >
            Start Interview →
          </button>

        </div>

      </section>


      {/* FEATURES */}

      <section className="features-section">

        <div className="section-heading">

          <span>
            PLATFORM FEATURES
          </span>

          <h2>
            Everything you need to prepare.
          </h2>

        </div>


        <div className="features-grid">

          {features.map((feature) => (

            <button
              className="feature-card"
              key={feature.number}
              onClick={() => setPage(feature.page)}
            >

              <span className="feature-number">
                {feature.number}
              </span>

              <span className="feature-arrow">
                ↗
              </span>

              <h3>
                {feature.title}
              </h3>

              <p>
                {feature.text}
              </p>

              <span className="feature-open">
                Open →
              </span>

            </button>

          ))}

        </div>

      </section>


      {/* FOOTER */}

      <footer className="home-footer">

        <strong>
          AI INTERVIEW PREPARATION SYSTEM
        </strong>

        <span>
          AI-powered interview preparation
        </span>

      </footer>

    </div>
  );
}

export default Home;