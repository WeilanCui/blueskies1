async function getHealth() {
  try {
    const response = await fetch("http://localhost:3000/api/health", {
      cache: "no-store",
    });

    if (!response.ok) {
      return { status: "error", upstreamStatus: response.status };
    }

    return response.json();
  } catch {
    return { status: "starting" };
  }
}

export default async function Home() {
  const health = await getHealth();

  const services = [
    ["Django", "API server on port 8000"],
    ["Postgres", "Primary relational database"],
    ["Redis", "Cache and Celery broker"],
    ["Celery", "Background worker process"],
    ["Next.js", "Frontend on port 3000"],
  ];

  return (
    <main className="shell">
      <nav className="topbar">
        <div className="brand">Blueskies</div>
        <div className="status" aria-label="Backend status">
          <span className="status-dot" />
          <span>{health.status ?? "unknown"}</span>
        </div>
      </nav>

      <section className="hero">
        <div>
          <h1>Full-stack app framework</h1>
          <p className="lede">
            A clean starting point with Django, PostgreSQL, Redis, Celery, Docker
            Compose, and a Next.js frontend already wired together.
          </p>
        </div>

        <div>
          <div className="stack">
            {services.map(([name, description]) => (
              <div className="service" key={name}>
                <strong>{name}</strong>
                <span>{description}</span>
              </div>
            ))}
          </div>

          <div className="health">
            <strong>Backend health</strong>
            <pre>{JSON.stringify(health, null, 2)}</pre>
          </div>
        </div>
      </section>
    </main>
  );
}
