"use client";

import { FieldError, Input, Label, TextField } from "@heroui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "../../components/Button";
import { type AuthResponse, getMe, login, signup } from "../../lib/appApi";
import styles from "./login.module.css";

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
  const [touched, setTouched] = useState({ email: false, password: false });

  const trimmedEmail = email.trim();
  const emailError =
    trimmedEmail.length === 0
      ? "Email is required."
      : !emailPattern.test(trimmedEmail)
        ? "Enter a valid email."
        : "";
  const passwordError = password.length === 0 ? "Password is required." : "";
  const canSubmit = !emailError && !passwordError;
  const showEmailError = touched.email ? emailError : "";
  const showPasswordError = touched.password ? passwordError : "";

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
  });
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
      router.replace(data.user.has_completed_intake ? "/home" : "/intake");
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
    setTouched({ email: true, password: true });
    if (!canSubmit || authMutation.isPending) {
      return;
    }
    setError(null);
    authMutation.mutate();
  }

  useEffect(() => {
    if (meQuery.isSuccess) {
      router.replace("/home");
    }
  }, [meQuery.isSuccess, router]);

  if (meQuery.isLoading || meQuery.isSuccess) {
    return (
      <main className={styles.authShell}>
        <p className="detail-muted">Checking your session...</p>
      </main>
    );
  }

  return (
    <main className={styles.authShell}>
      <section className={styles.authLayout}>
        <aside className={styles.authShowcase} aria-label="Blueskies preview">
          <Link className={styles.authBrand} href="/">
            Blueskies
          </Link>
          <div className={styles.authShowcaseCopy}>
            <p className="landing-eyebrow">Skin intelligence</p>
            <h1>Track what changes your skin.</h1>
            <p>
              Build a profile that connects skin state, product history,
              sensitivities, and daily context.
            </p>
          </div>
          <div className={styles.authPreviewStack} aria-hidden="true">
            <div className={styles.authPreviewCard}>
              <div>
                <span>Current focus</span>
                <strong>Barrier repair</strong>
              </div>
              <div className={styles.authPreviewMeter}>
                <span />
              </div>
            </div>
            <div className={styles.authPreviewGrid}>
              <div>
                <span>AM scan</span>
                <strong>3 products</strong>
              </div>
              <div>
                <span>Match</span>
                <strong>86%</strong>
              </div>
            </div>
            <div className={styles.authPreviewNote}>
              <span />
              <p>Fragrance sensitivity will be flagged during product scans.</p>
            </div>
          </div>
        </aside>

        <section className={styles.authPanel} aria-label="Account access">
          <div className={styles.authMobileBrand}>
            <Link className={styles.authBrand} href="/">
              Blueskies
            </Link>
          </div>
          <div className={styles.authCopy}>
            <p className="landing-eyebrow">Your skin profile</p>
            <h2>
              {mode === "signup" ? "Create your account." : "Welcome back."}
            </h2>
            <p>
              {mode === "signup"
                ? "Start with a mobile-friendly intake that can grow into product scans, tracking, and recommendations."
                : "Sign in to continue your intake and keep building your skincare profile."}
            </p>
          </div>

          <fieldset
            className={styles.authTabs}
            aria-label="Choose login or signup"
          >
            <button
              type="button"
              className={
                mode === "login"
                  ? [styles.authTab, styles.authTabActive].join(" ")
                  : styles.authTab
              }
              onClick={() => {
                setMode("login");
                setError(null);
              }}
            >
              Log in
            </button>
            <button
              type="button"
              className={
                mode === "signup"
                  ? [styles.authTab, styles.authTabActive].join(" ")
                  : styles.authTab
              }
              onClick={() => {
                setMode("signup");
                setError(null);
              }}
            >
              Sign up
            </button>
          </fieldset>

          <form className={styles.authForm} onSubmit={submit}>
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
              isInvalid={Boolean(showEmailError)}
              isRequired
              name="email"
              onBlur={() => setTouched((prev) => ({ ...prev, email: true }))}
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
              {showEmailError && <FieldError>{showEmailError}</FieldError>}
            </TextField>

            <TextField
              className="contact-field"
              isInvalid={Boolean(showPasswordError)}
              isRequired
              name="password"
              onBlur={() => setTouched((prev) => ({ ...prev, password: true }))}
              onChange={setPassword}
              type="password"
              value={password}
            >
              <Label>Password</Label>
              <Input
                autoComplete={
                  mode === "signup" ? "new-password" : "current-password"
                }
                name={mode === "signup" ? "new-password" : "current-password"}
                placeholder="Password"
                type="password"
                variant="secondary"
              />
              {showPasswordError && (
                <FieldError>{showPasswordError}</FieldError>
              )}
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

          <div className={styles.authFooterActions}>
            <Link href="/">Back to home</Link>
          </div>
        </section>
      </section>
    </main>
  );
}
