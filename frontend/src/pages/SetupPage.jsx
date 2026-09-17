import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { OptionBox, TopBar } from "../App.jsx";
import { createInterview } from "../api/interviews.js";
import { listResumes } from "../api/resumes.js";
import { getRoles } from "../api/roles.js";
import { ErrorBox, StatusLine } from "../components/StateViews.jsx";
import { DIFFICULTY_LABELS, INTERVIEW_TYPE_LABELS, PERSONA_LABELS } from "../lib/format.js";

const QUESTION_COUNTS = [5, 10, 15, 20].map((n) => ({ value: n, label: String(n) }));

export default function SetupPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const rolesQuery = useQuery({ queryKey: ["roles"], queryFn: getRoles });
  const resumesQuery = useQuery({ queryKey: ["resumes", 1], queryFn: () => listResumes(1, 50) });

  const roles = rolesQuery.data ?? [];
  const [role, setRole] = useState("");
  const [language, setLanguage] = useState("");
  const [interviewType, setInterviewType] = useState("MIXED");
  const [difficulty, setDifficulty] = useState("MEDIUM");
  const [persona, setPersona] = useState("PROFESSIONAL");
  const [questionCount, setQuestionCount] = useState(10);
  const [resumeId, setResumeId] = useState("");

  const selectedRole = useMemo(
    () => roles.find((r) => r.role === role) || null,
    [roles, role],
  );

  // Role capabilities come from the backend: only advertised values shown.
  const typeOptions = useMemo(() => {
    const allowed = selectedRole?.interview_types ?? ["TECHNICAL", "BEHAVIORAL", "MIXED"];
    return allowed.map((t) => ({ value: t, label: INTERVIEW_TYPE_LABELS[t] || t }));
  }, [selectedRole]);

  const difficultyOptions = useMemo(() => {
    const allowed = selectedRole?.difficulties ?? ["EASY", "MEDIUM", "HARD", "EXPERT"];
    return allowed.map((d) => ({ value: d, label: DIFFICULTY_LABELS[d] || d }));
  }, [selectedRole]);

  const languageOptions = useMemo(() => selectedRole?.languages ?? [], [selectedRole]);

  const resumes = resumesQuery.data?.items ?? [];

  const createMutation = useMutation({
    mutationFn: (payload) => createInterview(payload),
    onSuccess: (interview) => {
      queryClient.invalidateQueries({ queryKey: ["interviews"] });
      navigate(`/lobby/${interview.id}`);
    },
  });

  function onCreate() {
    if (!selectedRole) return;
    createMutation.mutate({
      resume_id: resumeId || null,
      target_role: selectedRole.role,
      programming_language: language || null,
      interview_type: interviewType,
      difficulty,
      interviewer_persona: persona,
      question_count: questionCount,
    });
  }

  return (
    <div className="app-page">
      <TopBar title="Interview Setup" />

      <div className="page-container">
        <div className="page-title">
          <span>02</span>
          <h1>Interview Setup</h1>
          <p>Configure your personalized interview.</p>
        </div>

        {rolesQuery.isPending ? <StatusLine>Loading supported roles…</StatusLine> : null}
        <ErrorBox error={rolesQuery.error} onRetry={() => rolesQuery.refetch()} />
        <ErrorBox error={resumesQuery.error} />
        <ErrorBox error={createMutation.error} onRetry={() => createMutation.reset()} />

        <div className="form-card setup-role-row">
          <label htmlFor="setup-role">Target Job Role</label>
          <select id="setup-role" value={role} onChange={(e) => { setRole(e.target.value); setLanguage(""); }} required>
            <option value="" disabled>
              Select a role…
            </option>
            {roles.map((r) => (
              <option key={r.role} value={r.role}>
                {r.role}
              </option>
            ))}
          </select>

          <label htmlFor="setup-language">Programming Language</label>
          <select
            id="setup-language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={!languageOptions.length}
          >
            <option value="">{languageOptions.length ? "No language preference" : "—"}</option>
            {languageOptions.map((lang) => (
              <option key={lang} value={lang}>
                {lang}
              </option>
            ))}
          </select>

          <label htmlFor="setup-resume">Resume (optional)</label>
          <select id="setup-resume" value={resumeId} onChange={(e) => setResumeId(e.target.value)}>
            <option value="">No resume</option>
            {resumes.map((resume) => (
              <option key={resume.id} value={resume.id}>
                {resume.filename}
              </option>
            ))}
          </select>
        </div>

        <div className="setup-grid">
          <OptionBox title="Interview Type" options={typeOptions} value={interviewType} onChange={setInterviewType} />
          <OptionBox title="Difficulty" options={difficultyOptions} value={difficulty} onChange={setDifficulty} />
          <OptionBox
            title="Interviewer Persona"
            options={Object.entries(PERSONA_LABELS).map(([value, label]) => ({ value, label }))}
            value={persona}
            onChange={setPersona}
          />
          <OptionBox title="Questions" options={QUESTION_COUNTS} value={questionCount} onChange={setQuestionCount} />
        </div>

        <button
          className="main-button center-button"
          type="button"
          disabled={!selectedRole || createMutation.isPending}
          onClick={onCreate}
        >
          {createMutation.isPending ? "Preparing interview…" : "Start Interview →"}
        </button>
      </div>
    </div>
  );
}
