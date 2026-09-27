import type { AuthGateway, AuthSession } from "./authGateway";

export type FakeAuthGateway = AuthGateway & {
  /** Test-only: push a session change through `onChange` listeners. */
  emit(session: AuthSession | null): void;
};

/** In-memory `AuthGateway` for tests; never talks to Supabase. */
export function createFakeAuthGateway(initial?: {
  configured?: boolean;
  session?: AuthSession | null;
  signInWithEmail?: (email: string) => Promise<void>;
}): FakeAuthGateway {
  const configured = initial?.configured ?? true;
  let session = initial?.session ?? null;
  const signInWithEmail = initial?.signInWithEmail ?? (async () => {});
  const listeners = new Set<(session: AuthSession | null) => void>();

  function emit(next: AuthSession | null) {
    session = next;
    listeners.forEach((listener) => listener(next));
  }

  return {
    isConfigured: () => configured,
    getSession: async () => session,
    onChange(callback) {
      listeners.add(callback);
      return () => listeners.delete(callback);
    },
    signInWithEmail,
    async signOut() {
      emit(null);
    },
    emit,
  };
}
