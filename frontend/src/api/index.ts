import { api } from "./client";
import { mockApi } from "./mock";

const useMock = import.meta.env.VITE_USE_MOCK_API === "true";

export const backend = useMock ? mockApi : api;
export { ApiError } from "./client";
