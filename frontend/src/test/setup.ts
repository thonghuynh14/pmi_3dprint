import "@testing-library/jest-dom/vitest";

import { afterAll, afterEach, beforeAll } from "vitest";

import { server } from "./msw/server";

// MSW lifecycle: bật trước test, reset sau mỗi test, tắt khi xong.
// onUnhandledRequest "error" → bắt typo URL trong test.
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
