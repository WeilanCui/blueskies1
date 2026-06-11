"use client";

import Link from "next/link";
import { FieldError, Input, Label, TextField } from "@heroui/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "../../components/Button";
import { login, signup, type AuthResponse } from "../../lib/appApi";

type AuthMode = "login" | "signup";

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const trimmedEmail = email.trim();
  const emailError =
    trimmedEmail.length === 0
      ? "Email is required."
      : !emailPattern.test(trimmedEmail)
        ? "Enter a valid email."
        : "";
  const passwordError = password.length === 0 ? "Password is required." : "";
  const canSubmit = !emailError && !passwordError;

  const authMutation = useMutation({
    mutationFn: () =>
      mode === "signup"
        ? signup({
            email: trimmedEmail,
            password,
            display_name: displayName.trim(),
          })
        : login({ identifier: trimmedEmail, password }),
    onSuccess: (data: AuthResponse) => {
      queryClient.setQueryData(["me"], data);
      router.replace("/intake");
    },
    onError: (submissionError) => {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : "Authentication failed.",
      );
    },
  });

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || authMutation.isPending) {
      return;
    }
    setError(null);
    authMutation.mutate();
  }

  return (
    <main className="auth-shell">
      <section className="auth-layout">
        <aside className="auth-showcase" aria-label="Blueskies preview">
          <Link className="auth-brand" href="/">
            Blueskies
          </Link>
          <div className="auth-showcase-copy">
            <p className="landing-eyebrow">Skin intelligence</p>
            <h1>Track what changes your skin.</h1>
            <p>
              Build a profile that connects skin state, product history,
              sensitivities, and daily context.
            </p>
          </div>
          <div className="auth-preview-stack" aria-hidden="true">
            <div className="auth-preview-card auth-preview-card-main">
              <div>
                <span>Current focus</span>
                <strong>Barrier repair</strong>
              </div>
              <div className="auth-preview-meter">
                <span />
              </div>
            </div>
            <div className="auth-preview-grid">
              <div>
                <span>AM scan</span>
                <strong>3 products</strong>
              </div>
              <div>
                <span>Match</span>
                <strong>86%</strong>
              </div>
            </div>
            <div className="auth-preview-note">
              <span />
              <p>Fragrance sensitivity will be flagged during product scans.</p>
            </div>
          </div>
        </aside>

        <section className="auth-panel" aria-label="Account access">
          <div className="auth-mobile-brand">
            <Link className="auth-brand" href="/">
              Blueskies
            </Link>
          </div>
          <div className="auth-copy">
            <p className="landing-eyebrow">Your skin profile</p>
            <h2>{mode === "signup" ? "Create your account." : "Welcome back."}</h2>
            <p>
              {mode === "signup"
                ? "Start with a mobile-friendly intake that can grow into product scans, tracking, and recommendations."
                : "Sign in to continue your intake and keep building your skincare profile."}
            </p>
          </div>

          <div className="auth-tabs" aria-label="Choose login or signup">
            <button
              type="button"
              className={mode === "login" ? "auth-tab auth-tab-active" : "auth-tab"}
              onClick={() => {
                setMode("login");
                setError(null);
              }}
            >
              Log in
            </button>
            <button
              type="button"
              className={mode === "signup" ? "auth-tab auth-tab-active" : "auth-tab"}
              onClick={() => {
                setMode("signup");
                setError(null);
              }}
            >
              Sign up
            </button>
          </div>

          <form className="auth-form" onSubmit={submit}>
            {mode === "signup" && (
              <TextField
                className="contact-field"
                name="display_name"
                onChange={setDisplayName}
                value={displayName}
              >
                <Label>Name</Label>
                <Input
                  autoComplete="name"
                  name="name"
                  placeholder="Your name"
                  variant="secondary"
                />
              </TextField>
            )}

            <TextField
              className="contact-field"
              isInvalid={Boolean(emailError)}
              isRequired
              name="email"
              onChange={setEmail}
              type="email"
              value={email}
          >
            <Label>Email</Label>
            <Input
              autoComplete="email"
              inputMode="email"
              name="email"
              placeholder="you@example.com"
              type="email"
              variant="secondary"
            />
            {emailError && <FieldError>{emailError}</FieldError>}
          </TextField>

            <TextField
              className="contact-field"
              isInvalid={Boolean(passwordError)}
              isRequired
              name="password"
              onChange={setPassword}
              type="password"
              value={password}
          >
            <Label>Password</Label>
            <Input
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              name={mode === "signup" ? "new-password" : "current-password"}
              placeholder="Password"
              type="password"
              variant="secondary"
            />
            {passwordError && <FieldError>{passwordError}</FieldError>}
          </TextField>

            <Button
              type="submit"
              fullWidth
              isDisabled={!canSubmit || authMutation.isPending}
              isPending={authMutation.isPending}
              size="lg"
            >
              {mode === "signup" ? "Create account" : "Log in"}
            </Button>

            {error && <p className="contact-error">{error}</p>}
          </form>

          <div className="auth-footer-actions">
            <Link href="/">Back to home</Link>
          </div>
        </section>
      </section>
    </main>
  );
}
