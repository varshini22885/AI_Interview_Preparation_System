import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { TopBar } from "../App.jsx";
import { deleteResume, listResumes, uploadResume } from "../api/resumes.js";
import { ErrorBox, EmptyState, StatusLine } from "../components/StateViews.jsx";
import { formatDateTime } from "../lib/format.js";

const ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx"];
const MAX_CLIENT_SIZE_BYTES = 10 * 1024 * 1024; // backend remains authoritative

function validateFile(file) {
  const lower = (file?.name || "").toLowerCase();
  if (!ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
    return "Unsupported file type. Please upload a PDF, DOC or DOCX file.";
  }
  if (file.size > MAX_CLIENT_SIZE_BYTES) {
    return "File is too large (10 MB limit).";
  }
  return null;
}

export default function ResumePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [clientError, setClientError] = useState(null);

  const resumesQuery = useQuery({
    queryKey: ["resumes", 1],
    queryFn: () => listResumes(1, 50),
  });

  const uploadMutation = useMutation({
    mutationFn: (file) => uploadResume(file),
    onSuccess: () => {
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => deleteResume(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resumes"] }),
  });

  function onChooseFile(event) {
    setClientError(null);
    const file = event.target.files?.[0] || null;
    if (!file) {
      setSelectedFile(null);
      return;
    }
    const problem = validateFile(file);
    if (problem) {
      setClientError({ code: "INVALID_FILE", message: problem });
      setSelectedFile(null);
      event.target.value = "";
      return;
    }
    setSelectedFile(file);
  }

  const resumes = resumesQuery.data?.items ?? [];

  return (
    <div className="app-page">
      <TopBar title="Resume Analysis" />

      <div className="page-container">
        <div className="page-title">
          <span>01</span>
          <h1>Resume & Role Analysis</h1>
          <p>Upload your resume, then configure your interview.</p>
        </div>

        <div className="resume-layout">
          <div className="resume-upload-card">
            <div className="upload-icon">↑</div>
            <h2>Upload Resume</h2>
            <p>PDF, DOC or DOCX</p>

            <input
              ref={fileInputRef}
              type="file"
              id="resume"
              name="resume"
              aria-label="Resume file"
              accept=".pdf,.doc,.docx"
              onChange={onChooseFile}
            />
            <label htmlFor="resume" className="upload-button">
              {selectedFile ? "Change File" : "Choose Resume"}
            </label>

            {selectedFile ? (
              <p className="selected-file" aria-live="polite">
                {selectedFile.name}
              </p>
            ) : null}

            <ErrorBox error={clientError} />
            <ErrorBox error={uploadMutation.error} onRetry={() => uploadMutation.reset()} />

            <button
              className="main-button"
              type="button"
              disabled={!selectedFile || uploadMutation.isPending}
              onClick={() => uploadMutation.mutate(selectedFile)}
            >
              {uploadMutation.isPending ? "Uploading…" : "Upload Resume"}
            </button>
          </div>

          <div className="form-card">
            <h2>Your resumes</h2>

            {resumesQuery.isPending ? <StatusLine>Loading resumes…</StatusLine> : null}
            <ErrorBox error={resumesQuery.error} onRetry={() => resumesQuery.refetch()} />

            {!resumesQuery.isPending && resumes.length === 0 ? (
              <EmptyState title="No resumes yet">
                <p>Upload your first resume to unlock personalized interviews.</p>
              </EmptyState>
            ) : null}

            <ul className="resume-list">
              {resumes.map((resume) => (
                <li key={resume.id} className="resume-item">
                  <div>
                    <strong>{resume.filename}</strong>
                    <small>
                      {formatDateTime(resume.created_at)} · {(resume.size_bytes / 1024).toFixed(0)} KB ·{" "}
                      {resume.parsed_at ? "Parsed" : "Processing"}
                    </small>
                  </div>
                  <button
                    type="button"
                    className="retry-button"
                    disabled={deleteMutation.isPending}
                    onClick={() => {
                      if (window.confirm(`Delete "${resume.filename}"?`)) deleteMutation.mutate(resume.id);
                    }}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>

            <ErrorBox error={deleteMutation.error} />

            <button className="main-button" type="button" onClick={() => navigate("/setup")}>
              Continue to Interview Setup →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
