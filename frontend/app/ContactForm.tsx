"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { FieldError, Input, Label, TextArea, TextField } from "@heroui/react";

import { Button } from "../components/Button";
import styles from "./ContactForm.module.css";

type ContactResponse = {
  detail?: string;
};

type ContactPayload = {
  name: string;
  email: string;
  feedback: string;
};

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

async function submitContact(payload: ContactPayload): Promise<ContactResponse> {
  const response = await fetch("/api/contact", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = (await response.json()) as unknown;

  if (!response.ok) {
    throw new Error(getContactErrorMessage(data));
  }

  return data as ContactResponse;
}

export default function ContactForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [feedback, setFeedback] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [showValidation, setShowValidation] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const contactMutation = useMutation({
    mutationKey: ["contactSubmission"],
    mutationFn: submitContact,
  });

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
  const feedbackError = trimmedFeedback.length === 0 ? "Feedback is required." : "";
  const canSubmit =
    trimmedName.length > 0 &&
    trimmedEmail.length > 0 &&
    hasValidEmail &&
    trimmedFeedback.length > 0;
  const isLocked = contactMutation.isPending || submitted;

  function revealValidation() {
    setShowValidation(true);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    revealValidation();
    if (isLocked) {
      return;
    }

    if (!canSubmit) {
      setMessage(null);
      setError("Please add your name, a valid email, and feedback before submitting.");
      return;
    }

    setMessage(null);
    setError(null);
    contactMutation.reset();

    contactMutation.mutate(
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
    <form className={styles.contactForm} onSubmit={handleSubmit}>
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
        {showValidation && feedbackError && <FieldError>{feedbackError}</FieldError>}
      </TextField>

      <Button type="submit" isDisabled={isLocked}>
        {contactMutation.isPending ? "Sending..." : submitted ? "Submitted" : "Send message"}
      </Button>

      {showValidation && !submitted && !canSubmit && (
        <p className="contact-help">Complete all fields with a valid email to send.</p>
      )}
      {message && <p className="contact-success">{message}</p>}
      {error && <p className="contact-error">{error}</p>}
    </form>
  );
}
