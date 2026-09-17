import { Link } from "react-router-dom";
import { TopBar } from "../App.jsx";

export default function NotFoundPage() {
  return (
    <div className="app-page">
      <TopBar title="Not Found" />
      <div className="page-container">
        <div className="page-title">
          <span>404</span>
          <h1>Page not found</h1>
          <p>The page you are looking for does not exist.</p>
        </div>
        <Link className="main-button center-button" to="/">
          Back to Home
        </Link>
      </div>
    </div>
  );
}
