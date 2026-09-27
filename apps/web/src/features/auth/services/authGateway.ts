export type AuthSession = {
  accessToken: string;
  userId: string;
  email: string;
};

/** Our own seam over whatever auth provider sits behind it (Supabase today). */
export interface AuthGateway {
  isConfigured(): boolean;
  getSession(): Promise<AuthSession | null>;
  onChange(callback: (session: AuthSession | null) => void): () => void;
  signInWithEmail(email: string): Promise<void>;
  signOut(): Promise<void>;
}
