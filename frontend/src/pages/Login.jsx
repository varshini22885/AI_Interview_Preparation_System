import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { TopBar } from "../App.jsx";
import { useAuth } from "../auth/AuthContext.jsx";
import { ErrorBox } from "../components/StateViews.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await login(email.trim(), password);
      navigate(location.state?.from || "/resume", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="app-page">
      <TopBar title="Sign In" />
      <div className="page-container">
        <div className="page-title">
          <span>00</span>
          <h1>Sign In</h1>
          <p>Access your interview preparation workspace.</p>
        </div>

        <form className="form-card" onSubmit={onSubmit} noValidate>
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <ErrorBox error={error} />

          <button className="main-button" type="submit" disabled={pending || !email || !password}>
            {pending ? "Signing in…" : "Sign In →"}
          </button>

          <p className="form-hint">
            No account yet? <Link to="/register">Create one</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
