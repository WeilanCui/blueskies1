"use client";

import { FieldError, Input, Label, TextArea, TextField } from "@heroui/react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "../components/Button";
import { getMe } from "../lib/appApi";
import styles from "./ContactForm.module.css";

type ContactResponse = {
  detail?: string;
  alreadyVerified?: boolean;
};

type FeedbackPayload = {
  name: string;
  email: string;
  feedback: string;
};

type BetaSignupPayload = {
  email: string;
};

type ContactVerificationPayload = {
  email: string;
  code: string;
};

type BetaStep = "email" | "code" | "verified";

function getContactErrorMessage(data: unknown): string {
  if (data && typeof data === "object") {
    const detail = "detail" in data ? data.detail : undefined;
    if (typeof detail === "string") {
      return detail;
    }

    const firstFieldError = Object.values(data)
      .flatMap((value) => (Array.isArray(value) ? value : [value]))
      .find((value) => typeof value === "string");
    if (typeof firstFieldError === "string") {
      return firstFieldError;
    }
  }

  return "Could not send your message.";
}

async function postContactJson(
  path: string,
  payload: BetaSignupPayload | ContactVerificationPayload | FeedbackPayload,
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

function requestBetaCode(payload: BetaSignupPayload): Promise<ContactResponse> {
  return postContactJson("/api/contact/request-code", payload);
}

function verifyBetaCode(
  payload: ContactVerificationPayload,
): Promise<ContactResponse> {
  return postContactJson("/api/contact/verify-code", payload);
}

function submitFeedback(payload: FeedbackPayload): Promise<ContactResponse> {
  return postContactJson("/api/contact", payload);
}

function BetaSignupForm() {
  const router = useRouter();
  const [step, setStep] = useState<BetaStep>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showValidation, setShowValidation] = useState(false);
  const requestCodeMutation = useMutation({
    mutationKey: ["betaVerificationRequest"],
    mutationFn: requestBetaCode,
  });
  const verifyCodeMutation = useMutation({
    mutationKey: ["betaVerificationCheck"],
    mutationFn: verifyBetaCode,
  });

  const trimmedEmail = email.trim().toLowerCase();
  const trimmedCode = code.trim();
  const hasValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail);
  const hasValidCode = /^\d{6}$/.test(trimmedCode);
  const isBusy = requestCodeMutation.isPending || verifyCodeMutation.isPending;

  function continueToSignup() {
    router.push(
      `/login?mode=signup&email=${encodeURIComponent(trimmedEmail)}&verified=1`,
    );
  }

  function resetToEmail() {
    setStep("email");
    setCode("");
    setMessage(null);
    setError(null);
    setShowValidation(false);
    requestCodeMutation.reset();
    verifyCodeMutation.reset();
  }

  function handleRequestCode(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setShowValidation(true);
    if (isBusy) {
      return;
    }
    if (!hasValidEmail) {
      setMessage(null);
      setError("Enter a valid email address.");
      return;
    }

    setMessage(null);
    setError(null);
    requestCodeMutation.reset();
    verifyCodeMutation.reset();

    requestCodeMutation.mutate(
      { email: trimmedEmail },
      {
        onSuccess: (data) => {
          if (data.alreadyVerified) {
            setStep("verified");
            setMessage(
              data.detail ?? "You're already verified for early access.",
            );
            return;
          }
          setStep("code");
          setMessage(
            data.detail ??
              "Check your email for a six-digit verification code.",
          );
        },
        onError: (submissionError) => {
          setError(
            submissionError instanceof Error
              ? submissionError.message
              : "Could not send the code.",
          );
        },
      },
    );
  }

  function handleVerifyCode(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isBusy) {
      return;
    }
    if (!hasValidCode) {
      setMessage(null);
      setError("Enter the six-digit code.");
      return;
    }

    setMessage(null);
    setError(null);
    verifyCodeMutation.reset();

    verifyCodeMutation.mutate(
      { email: trimmedEmail, code: trimmedCode },
      {
        onSuccess: (data) => {
          setStep("verified");
          setMessage(data.detail ?? "You're verified for early access.");
        },
        onError: (verificationError) => {
          setError(
            verificationError instanceof Error
              ? verificationError.message
              : "Could not verify the code.",
          );
        },
      },
    );
  }

  if (step === "verified") {
    return (
      <div
        className={[styles.betaSignup, styles.verifiedState].join(" ")}
        role="status"
      >
        <div>
          <strong>You're verified.</strong>
          <p>{message ?? "Continue to create your profile and password."}</p>
        </div>
        <button
          className={styles.betaButton}
          onClick={continueToSignup}
          type="button"
        >
          Continue to create profile
          <span aria-hidden="true">→</span>
        </button>
      </div>
    );
  }

  if (step === "code") {
    return (
      <form className={styles.betaSignup} onSubmit={handleVerifyCode}>
        <label className={styles.betaLabel} htmlFor="beta-code">
          Enter the verification code
        </label>
        <div className={styles.betaInputRow}>
          <input
            id="beta-code"
            inputMode="numeric"
            maxLength={6}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
            pattern="[0-9]{6}"
            placeholder="000000"
            value={code}
          />
          <button
            className={styles.betaButton}
            disabled={isBusy || !hasValidCode}
            type="submit"
          >
            {verifyCodeMutation.isPending ? "Checking..." : "Verify email"}
            <span aria-hidden="true">→</span>
          </button>
        </div>
        <div className={styles.betaMeta}>
          <p>{message ?? `Sent to ${trimmedEmail}.`}</p>
          <button onClick={resetToEmail} type="button">
            Use another email
          </button>
        </div>
        {error && <p className="contact-error">{error}</p>}
      </form>
    );
  }

  return (
    <form className={styles.betaSignup} onSubmit={handleRequestCode}>
      <label className={styles.betaLabel} htmlFor="beta-email">
        Join the private beta
      </label>
      <div className={styles.betaInputRow}>
        <input
          autoComplete="email"
          id="beta-email"
          inputMode="email"
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
          type="email"
          value={email}
        />
        <button className={styles.betaButton} disabled={isBusy} type="submit">
          {requestCodeMutation.isPending ? "Sending..." : "Get early access"}
          <span aria-hidden="true">→</span>
        </button>
      </div>
      <p className={styles.betaNote}>
        We'll email a verification code. No spam, no sold data.
      </p>
      {showValidation && !hasValidEmail && (
        <p className="contact-error">Enter a valid email address.</p>
      )}
      {error && <p className="contact-error">{error}</p>}
    </form>
  );
}

function FeedbackForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [feedback, setFeedback] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [showValidation, setShowValidation] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const feedbackMutation = useMutation({
    mutationKey: ["feedbackSubmission"],
    mutationFn: submitFeedback,
  });
  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
  });

  useEffect(() => {
    const userEmail = meQuery.data?.user.email;
    if (userEmail && email.trim().length === 0) {
      setEmail(userEmail);
    }
  }, [email, meQuery.data?.user.email]);

  const trimmedName = name.trim();
  const trimmedEmail = email.trim();
  const trimmedFeedback = feedback.trim();
  const hasValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail);
  const nameError = trimmedName.length === 0 ? "Name is required." : "";
  const emailError =
    trimmedEmail.length === 0
      ? "Email is required."
      : !hasValidEmail
        ? "Enter a valid email address."
        : "";
  const feedbackError =
    trimmedFeedback.length === 0 ? "Feedback is required." : "";
  const canSubmit =
    trimmedName.length > 0 &&
    trimmedEmail.length > 0 &&
    hasValidEmail &&
    trimmedFeedback.length > 0;
  const isLocked = feedbackMutation.isPending || submitted;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setShowValidation(true);
    if (isLocked) {
      return;
    }

    if (!canSubmit) {
      setMessage(null);
      setError(
        "Please add your name, a valid email, and feedback before submitting.",
      );
      return;
    }

    setMessage(null);
    setError(null);
    feedbackMutation.reset();

    feedbackMutation.mutate(
      {
        name: trimmedName,
        email: trimmedEmail,
        feedback: trimmedFeedback,
      },
      {
        onSuccess: (data) => {
          setSubmitted(true);
          setMessage(data.detail ?? "Thanks. We will reach out shortly.");
        },
        onError: (submissionError) => {
          setError(
            submissionError instanceof Error
              ? submissionError.message
              : "Could not reach the backend API.",
          );
        },
      },
    );
  }

  return (
    <form className={styles.feedbackForm} onSubmit={handleSubmit}>
      <TextField
        className="contact-field"
        isDisabled={isLocked}
        isInvalid={showValidation && Boolean(nameError)}
        name="name"
        onChange={setName}
        value={name}
      >
        <Label>Name</Label>
        <Input placeholder="Your name" variant="secondary" />
        {showValidation && nameError && <FieldError>{nameError}</FieldError>}
      </TextField>

      <TextField
        className="contact-field"
        isDisabled={isLocked}
        isInvalid={showValidation && Boolean(emailError)}
        name="email"
        onChange={setEmail}
        type="email"
        value={email}
      >
        <Label>Email</Label>
        <Input placeholder="you@example.com" variant="secondary" />
        {showValidation && emailError && <FieldError>{emailError}</FieldError>}
      </TextField>

      <TextField
        className="contact-field"
        isDisabled={isLocked}
        isInvalid={showValidation && Boolean(feedbackError)}
        name="feedback"
        onChange={setFeedback}
        value={feedback}
      >
        <Label>Feedback</Label>
        <TextArea
          placeholder="Tell us what you want Blueskies to help with."
          rows={5}
          variant="secondary"
        />
        {showValidation && feedbackError && (
          <FieldError>{feedbackError}</FieldError>
        )}
      </TextField>

      <Button type="submit" isDisabled={isLocked}>
        {feedbackMutation.isPending
          ? "Sending..."
          : submitted
            ? "Submitted"
            : "Send feedback"}
      </Button>

      {showValidation && !submitted && !canSubmit && (
        <p className="contact-help">
          Complete all fields with a valid email to send.
        </p>
      )}
      {message && <p className="contact-success">{message}</p>}
      {error && <p className="contact-error">{error}</p>}
    </form>
  );
}

export default function ContactForm() {
  return (
    <div className={styles.contactStack}>
      <BetaSignupForm />
      <section
        className={styles.feedbackPanel}
        aria-labelledby="feedback-title"
      >
        <div>
          <p className="landing-eyebrow">Feedback</p>
          <h3 id="feedback-title">
            Questions, Concerns, Comments? We want to hear from you.
          </h3>
          <p>
            Share notes for the team separately from the early access signup.
          </p>
        </div>
        <FeedbackForm />
      </section>
    </div>
  );
}
