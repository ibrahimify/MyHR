"use client";

import { FormEvent, useState } from "react";
import { Building2, LoaderCircle, LogIn } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { getSupabaseBrowserClient, usesSupabaseAuth } from "@/lib/supabase";

export default function LoginPage() {
  const { ready, user } = useAuth();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const client = getSupabaseBrowserClient();
    if (!client) {
      setError("Supabase authentication is not configured.");
      setSubmitting(false);
      return;
    }
    const { error: signInError } = await client.auth.signInWithPassword({
      email: String(data.get("email") ?? "").trim(),
      password: String(data.get("password") ?? ""),
    });
    if (signInError) {
      setError("The email or password is incorrect.");
      setSubmitting(false);
    }
  }

  if (!usesSupabaseAuth || (ready && user)) return null;
  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <span className="login-mark"><Building2 size={25} /></span>
        <p className="eyebrow">MyHR workspace</p>
        <h1 id="login-title">Sign in</h1>
        <p>Use the account assigned by your organization administrator.</p>
        <form onSubmit={submit}>
          {error && <div className="form-alert" role="alert">{error}</div>}
          <label className="field">
            <span>Email</span>
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label className="field">
            <span>Password</span>
            <input name="password" type="password" autoComplete="current-password" required />
          </label>
          <button className="button button-primary" disabled={submitting} type="submit">
            {submitting ? <LoaderCircle className="spin" size={17} /> : <LogIn size={17} />}
            {submitting ? "Signing in" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
