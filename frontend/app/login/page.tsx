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
type SignupStep = "verifyEmail" | "verifyCode" | "account";

type ContactResponse = {
  detail?: string;
  alreadyVerified?: boolean;
};

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const codePattern = /^\d{6}$/;

function getContactErrorMessage(data: unknown): string {
  if (data && typeof data === "object") {
    const detail = "detail" in data ? data.detail : undefined;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return "Something went wrong. Please try again.";
}

async function postContactJson(
  path: string,
  payload: Record<string, string>,
): Promise<ContactResponse> {
  const response = await fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = (await response.json().catch(() => ({}))) as unknown;
  if (!response.ok) {
    throw new Error(getContactErrorMessage(data));
  }
  return data as ContactResponse;
}

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<AuthMode>("login");
  const [signupStep, setSignupStep] = useState<SignupStep>("verifyEmail");
  const [email, setEmail] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [verificationMessage, setVerificationMessage] = useState<string | null>(
    null,
  );
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
  const verificationCodeError = codePattern.test(verificationCode)
    ? ""
    : "Enter the six-digit code.";
  const canSubmit =
    mode === "login"
      ? !emailError && !passwordError
      : signupStep === "verifyEmail"
        ? !emailError
        : signupStep === "verifyCode"
          ? !verificationCodeError
          : !emailError && !passwordError;
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
  const requestCodeMutation = useMutation({
    mutationFn: () =>
      postContactJson("/api/contact/request-code", { email: trimmedEmail }),
    onSuccess: (data) => {
      setError(null);
      if (data.alreadyVerified) {
        setSignupStep("account");
        setVerificationMessage(
          data.detail ?? "Your email is verified. Create your password.",
        );
        return;
      }
      setSignupStep("verifyCode");
      setVerificationMessage(
        data.detail ?? "Check your email for a six-digit verification code.",
      );
    },
    onError: (submissionError) => {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : "Could not send the code.",
      );
    },
  });
  const verifyCodeMutation = useMutation({
    mutationFn: () =>
      postContactJson("/api/contact/verify-code", {
        email: trimmedEmail,
        code: verificationCode,
      }),
    onSuccess: (data) => {
      setError(null);
      setSignupStep("account");
      setVerificationMessage(
        data.detail ?? "Your email is verified. Create your password.",
      );
    },
    onError: (submissionError) => {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : "Could not verify the code.",
      );
    },
  });

  const isPending =
    authMutation.isPending ||
    requestCodeMutation.isPending ||
    verifyCodeMutation.isPending;

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("mode") === "signup") {
      setMode("signup");
      if (params.get("verified") === "1") {
        setSignupStep("account");
        setVerificationMessage("Your email is verified. Create your password.");
      }
    }
    const emailParam = params.get("email");
    if (emailParam) {
      setEmail(emailParam);
    }
  }, []);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched({
      email: true,
      password: mode === "login" || signupStep === "account",
    });
    if (!canSubmit || isPending) {
      return;
    }
    setError(null);

    if (mode === "signup" && signupStep === "verifyEmail") {
      requestCodeMutation.mutate();
      return;
    }
    if (mode === "signup" && signupStep === "verifyCode") {
      verifyCodeMutation.mutate();
      return;
    }

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
                ? "Verify your email from the private beta form first, then create your password and start the mobile-friendly intake."
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
                setVerificationMessage(null);
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
                setSignupStep("verifyEmail");
                setVerificationCode("");
                setVerificationMessage(null);
              }}
            >
              Sign up
            </button>
          </fieldset>

          <form className={styles.authForm} onSubmit={submit}>
            {mode === "signup" && signupStep === "account" && (
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
              onChange={(value) => {
                setEmail(value);
                if (mode === "signup") {
                  setSignupStep("verifyEmail");
                  setVerificationCode("");
                  setVerificationMessage(null);
                }
              }}
              type="email"
              value={email}
            >
              <Label>Email</Label>
              <Input
                autoComplete="email"
                inputMode="email"
                disabled={mode === "signup" && signupStep !== "verifyEmail"}
                name="email"
                placeholder="you@example.com"
                type="email"
                variant="secondary"
              />
              {showEmailError && <FieldError>{showEmailError}</FieldError>}
            </TextField>

            {mode === "signup" && signupStep === "verifyCode" && (
              <TextField
                className="contact-field"
                isInvalid={Boolean(error) && Boolean(verificationCodeError)}
                name="verification_code"
                onChange={(value) =>
                  setVerificationCode(value.replace(/\D/g, ""))
                }
                value={verificationCode}
              >
                <Label>Verification code</Label>
                <Input
                  inputMode="numeric"
                  maxLength={6}
                  name="verification_code"
                  placeholder="000000"
                  variant="secondary"
                />
              </TextField>
            )}

            {(mode === "login" || signupStep === "account") && (
              <TextField
                className="contact-field"
                isInvalid={Boolean(showPasswordError)}
                isRequired
                name="password"
                onBlur={() =>
                  setTouched((prev) => ({ ...prev, password: true }))
                }
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
            )}

            {mode === "signup" && verificationMessage && (
              <p className="contact-success">{verificationMessage}</p>
            )}

            {mode === "signup" && signupStep === "verifyCode" && (
              <p className="contact-help">
                Enter the code sent to {trimmedEmail.toLowerCase()}.{" "}
                <button
                  type="button"
                  onClick={() => {
                    setSignupStep("verifyEmail");
                    setVerificationCode("");
                    setVerificationMessage(null);
                    setError(null);
                  }}
                >
                  Use another email.
                </button>
              </p>
            )}


            <Button
              type="submit"
              fullWidth
              isDisabled={!canSubmit || isPending}
              isPending={isPending}
              size="lg"
            >
              {mode === "login"
                ? "Log in"
                : signupStep === "verifyEmail"
                  ? "Get early access"
                  : signupStep === "verifyCode"
                    ? "Verify email"
                    : "Create account"}
            </Button>

            {error && (
              <p className="contact-error">
                {error}
                {mode === "signup" &&
                  error.toLowerCase().includes("verify your email") && (
                    <>
                      {" "}
                      <Link href="/#contact">Join the private beta.</Link>
                    </>
                  )}
              </p>
            )}
          </form>

          <div className={styles.authFooterActions}>
            <Link href="/">Back to home</Link>
          </div>
        </section>
      </section>
    </main>
  );
}
