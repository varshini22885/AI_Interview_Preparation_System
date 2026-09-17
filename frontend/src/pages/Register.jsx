import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { TopBar } from "../App.jsx";
import { useAuth } from "../auth/AuthContext.jsx";
import { ErrorBox } from "../components/StateViews.jsx";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError({ code: "WEAK_PASSWORD", message: "Password must be at least 8 characters." });
      return;
    }
    setPending(true);
    try {
      await register(email.trim(), fullName.trim(), password);
      navigate("/resume", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="app-page">
      <TopBar title="Create Account" />
      <div className="page-container">
        <div className="page-title">
          <span>00</span>
          <h1>Create Account</h1>
          <p>Start practicing with AI-powered interviews.</p>
        </div>

        <form className="form-card" onSubmit={onSubmit} noValidate>
          <label htmlFor="reg-name">Full name</label>
          <input
            id="reg-name"
            type="text"
            autoComplete="name"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />

          <label htmlFor="reg-email">Email</label>
          <input
            id="reg-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <label htmlFor="reg-password">Password (8+ characters)</label>
          <input
            id="reg-password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <ErrorBox error={error} />

          <button className="main-button" type="submit" disabled={pending || !email || !password || !fullName}>
            {pending ? "Creating account…" : "Create Account →"}
          </button>

          <p className="form-hint">
            Already registered? <Link to="/login">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
