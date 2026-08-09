"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AppPageHeader } from "../../components/AppPageHeader";
import { Button } from "../../components/Button";
import { ScoreBadge } from "../../components/ScoreBadge";
import { getMe, getRankedRecommendations } from "../../lib/appApi";
import styles from "./recommendations.module.css";

const authFreshMs = 5 * 60 * 1000;

function RecommendationsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [page, setPage] = useState(1);
  const [includeExcluded, setIncludeExcluded] = useState(false);

  // Parse includeExcluded from search params
  useEffect(() => {
    const param = searchParams.get("include_excluded");
    setIncludeExcluded(param === "true");
  }, [searchParams]);

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: authFreshMs,
  });

  const recommendationsQuery = useQuery({
    queryKey: ["recommendations", page, includeExcluded],
    queryFn: () => getRankedRecommendations(includeExcluded, page),
    enabled: meQuery.isSuccess,
  });

  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  function handleIncludeExcludedChange() {
    const newValue = !includeExcluded;
    setIncludeExcluded(newValue);
    setPage(1);
    // Update URL without navigation
    const params = new URLSearchParams();
    if (newValue) {
      params.set("include_excluded", "true");
    }
    router.push(
      newValue ? `/recommendations?${params.toString()}` : "/recommendations",
      { scroll: false },
    );
  }

  if (meQuery.isLoading || meQuery.isError) {
    return <p className="detail-muted">Loading your session...</p>;
  }

  const recommendations = recommendationsQuery.data?.results ?? [];
  const hasNext = !!recommendationsQuery.data?.next;
  const hasPrev = !!recommendationsQuery.data?.previous;

  return (
    <div className={styles.layout}>
      <AppPageHeader
        title="For You"
        description="Ranked products matching your skin profile."
        action={
          <label className={styles.toggleLabel}>
            <input
              type="checkbox"
              checked={includeExcluded}
              onChange={handleIncludeExcludedChange}
              disabled={recommendationsQuery.isLoading}
            />
            <span>Show avoided</span>
          </label>
        }
      />

      {recommendationsQuery.isLoading ? (
        <p className="detail-muted">Loading recommendations...</p>
      ) : recommendationsQuery.isError ? (
        <p className="detail-muted">Could not load recommendations.</p>
      ) : recommendations.length === 0 ? (
        <div className={styles.emptyState}>
          <p>
            {includeExcluded
              ? "No recommendations to show."
              : "No products match your profile yet. Check back after adding skin concerns."}
          </p>
        </div>
      ) : (
        <>
          <section
            className={styles.listSection}
            aria-label="Ranked recommendations"
          >
            <ul className={styles.list}>
              {recommendations.map((match) => (
                <li key={match.formulation_id} className={styles.listItem}>
                  <div className={styles.productInfo}>
                    <div>
                      <span className={styles.brand}>{match.brand_name}</span>
                      <h2 className={styles.productName}>
                        {match.product_name}
                      </h2>
                    </div>
                    {match.reasons.length > 0 && (
                      <p className={styles.reason}>{match.reasons[0]}</p>
                    )}
                    {match.coverage.length > 0 && (
                      <ul className={styles.coverage}>
                        {match.coverage.map((cov) => (
                          <li key={cov.concern} className={styles.coverageLine}>
                            <span className={styles.coverageLabel}>
                              {cov.concern_label}:
                            </span>{" "}
                            {cov.matched}/{cov.total} active
                            {cov.matched_rules.length > 0 && (
                              <>
                                {" — "}
                                {cov.matched_rules.slice(0, 2).join(", ")}
                                {cov.matched_rules.length > 2 ? `…` : ""}
                              </>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                    {match.confidence_band === "low" && (
                      <p className={styles.reason}>Limited ingredient data</p>
                    )}
                  </div>
                  <ScoreBadge
                    score={match.final_score}
                    excluded={match.excluded}
                    hasWarnings={match.warnings.length > 0}
                  />
                </li>
              ))}
            </ul>
          </section>

          {(hasNext || hasPrev) && (
            <section className={styles.paginationSection}>
              <Button
                variant="secondary"
                onPress={() => setPage((p) => Math.max(1, p - 1))}
                isDisabled={!hasPrev || recommendationsQuery.isLoading}
              >
                Previous
              </Button>
              <span className={styles.pageIndicator}>Page {page}</span>
              <Button
                variant="secondary"
                onPress={() => setPage((p) => p + 1)}
                isDisabled={!hasNext || recommendationsQuery.isLoading}
              >
                Next
              </Button>
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default function RecommendationsPage() {
  return (
    <Suspense
      fallback={<p className="detail-muted">Loading recommendations…</p>}
    >
      <RecommendationsContent />
    </Suspense>
  );
}
