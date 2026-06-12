"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppTabNav } from "../../components/AppTabNav";
import { Button } from "../../components/Button";
import { getMe, logout } from "../../lib/appApi";
import styles from "./scan.module.css";

const authFreshMs = 5 * 60 * 1000;

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ScanPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: authFreshMs,
  });
  const logoutMutation = useMutation({
    mutationFn: logout,
    onSettled: () => {
      queryClient.clear();
      router.replace("/login");
    },
  });

  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  function selectImage(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    event.target.value = "";
  }

  if (meQuery.isLoading || meQuery.isError) {
    return (
      <main className={styles.scanShell}>
        <p className="detail-muted">Loading your session...</p>
      </main>
    );
  }

  return (
    <main className={styles.scanShell}>
      <nav className={["topbar", styles.scanTopbar].join(" ")}>
        <Link className="brand" href="/">
          Blueskies
        </Link>
        <Button
          type="button"
          variant="ghost"
          isDisabled={logoutMutation.isPending}
          onPress={() => logoutMutation.mutate()}
        >
          Log out
        </Button>
      </nav>
      <AppTabNav active="scan" />

      <div className={styles.scanLayout}>
        <section className={styles.scanHero}>
          <p className="landing-eyebrow">Scan</p>
          <h1>Capture a product or skin photo.</h1>
          <p>
            Take a photo or upload one from your phone. Product and facial
            analysis will connect here as the scanner backend comes online.
          </p>
        </section>

        <section className={styles.scanPanel}>
          <div className={styles.scanPreview}>
            {previewUrl ? (
              <img alt="Selected scan preview" src={previewUrl} />
            ) : (
              <div className={styles.scanPlaceholder}>
                <strong>No photo selected</strong>
                <span>
                  Use your camera for a product, barcode, ingredient list, or
                  skin-progress photo.
                </span>
              </div>
            )}
          </div>

          <div className={styles.scanActions}>
            <label className={styles.fileAction}>
              Take photo
              <input
                accept="image/*"
                capture="environment"
                className={styles.fileInput}
                onChange={selectImage}
                type="file"
              />
            </label>
            <label className={[styles.fileAction, styles.fileActionSecondary].join(" ")}>
              Upload photo
              <input
                accept="image/*"
                className={styles.fileInput}
                onChange={selectImage}
                type="file"
              />
            </label>

            {selectedFile && (
              <div className={styles.scanMeta}>
                <strong>{selectedFile.name}</strong>
                <span>{formatBytes(selectedFile.size)}</span>
              </div>
            )}

            <p className={styles.scanNote}>
              This preview stays on your device in this pass. No image is sent
              to the backend yet.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
