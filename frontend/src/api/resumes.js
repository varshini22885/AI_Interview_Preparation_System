import { api } from "./client";

/** GET /resumes?page&page_size -> { items, page, page_size, total } */
export function listResumes(page = 1, pageSize = 20) {
  return api.get(`/resumes?page=${page}&page_size=${pageSize}`);
}

/** POST /resumes (multipart) -> resume */
export function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);
  return api.postForm("/resumes", formData);
}

/** GET /resumes/{id} -> resume */
export function getResume(id) {
  return api.get(`/resumes/${id}`);
}

/** DELETE /resumes/{id} */
export function deleteResume(id) {
  return api.del(`/resumes/${id}`);
}
