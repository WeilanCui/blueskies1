"use client";

import { useRef, type ReactNode } from "react";
import { Button, type AppButtonVariant } from "./Button";

type UploadButtonProps = {
  accept?: string;
  children: ReactNode;
  onFileSelect: (file: File) => void;
  variant?: AppButtonVariant;
};

export function UploadButton({
  accept = "image/*",
  children,
  onFileSelect,
  variant = "primary",
}: UploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFileSelect(file);
        }}
      />
      <Button variant={variant} onPress={() => inputRef.current?.click()}>
        {children}
      </Button>
    </>
  );
}
