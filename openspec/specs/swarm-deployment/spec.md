# swarm-deployment Specification

## Purpose
TBD - created by archiving change add-swarm-service-compose. Update Purpose after archive.
## Requirements
### Requirement: The stack deploys from a single Swarm compose file

The repository SHALL provide `service-compose.yml`, deployable with
`docker stack deploy -c service-compose.yml blueskies1`, declaring every service the
application needs to run.

#### Scenario: Deploying the stack

- **WHEN** the operator deploys the stack file to a Swarm manager
- **THEN** services for the Next.js frontend, Django backend, Celery worker, Celery beat,
  PostgreSQL, and Redis are created
- **AND** each service references an image from the configured registry rather than a build context

#### Scenario: The file is valid Swarm input

- **WHEN** the stack file is validated
- **THEN** it parses without error
- **AND** it declares no keys that Swarm mode silently ignores, such as `build`, `depends_on`, or `profiles`

### Requirement: Exactly one service is externally reachable

The Next.js service SHALL be the only service reachable from outside the Swarm. All other
services SHALL be reachable only on the stack's private overlay network.

#### Scenario: Public routing

- **WHEN** a request arrives for the application's public hostname
- **THEN** Traefik routes it over TLS to the Next.js service
- **AND** the request is served without exposing Django, Celery, PostgreSQL, or Redis to the outside

#### Scenario: Backend access from the browser

- **WHEN** the browser calls an application API route
- **THEN** the request is handled by a Next.js route handler
- **AND** that handler proxies to Django over the private network

#### Scenario: Django admin access

- **WHEN** an operator requests the Django admin path through the public hostname
- **THEN** the request is proxied to the Django service
- **AND** the admin's own static assets are served so the page renders styled

### Requirement: Images are runnable without an externally supplied command

Each production image SHALL declare its own default command, so a Swarm service definition
need not supply one.

#### Scenario: Starting the backend image

- **WHEN** the backend production image is run with no command override
- **THEN** it serves the Django application through a production WSGI server
- **AND** it does not use the Django development server

#### Scenario: Starting the frontend image

- **WHEN** the frontend production image is run with no command override
- **THEN** it serves the built Next.js application
- **AND** it does not run a development server or rebuild on start

#### Scenario: Development images are preserved

- **WHEN** the local development stack is started
- **THEN** each service builds its development stage and behaves exactly as before this change
- **AND** source bind-mounts and hot reload continue to work

### Requirement: Database migrations are applied by exactly one service

Migrations SHALL be applied automatically on deployment, by the Django service alone. The
Celery worker and beat services share the same image and SHALL NOT apply migrations.

#### Scenario: Deploying a change containing migrations

- **WHEN** the stack is deployed with pending migrations
- **THEN** the Django service applies them before it begins serving requests
- **AND** no other service attempts to apply them

#### Scenario: A service that does not migrate is scheduled first

- **WHEN** the Celery worker or beat service starts while migrations are still being applied
- **THEN** it waits for the schema to be current before executing its command
- **AND** it fails its task rather than waiting indefinitely if the bound is exceeded

#### Scenario: A migration outlasts the health grace period

- **WHEN** applying migrations takes longer than the service's health `start_period`
- **THEN** the service continues to report healthy for as long as the migration is running
- **AND** the task is not stopped part-way through it

#### Scenario: A migration is blocked by another session's lock

- **WHEN** a migration cannot acquire a lock it needs
- **THEN** it fails within a bounded time rather than waiting indefinitely
- **AND** the task exits so the restart policy retries it

#### Scenario: A migration fails

- **WHEN** applying migrations fails
- **THEN** the service task fails visibly rather than starting and serving against a stale schema

#### Scenario: Concurrency is bounded

- **WHEN** the Django service is scheduled
- **THEN** exactly one replica of it runs, so two replicas cannot migrate concurrently

### Requirement: Credentials are supplied as Swarm secrets

The stack file SHALL NOT contain credential values. The Django secret key and the database
password SHALL be supplied as Swarm secrets and referenced by name, and services SHALL
consume them through `*_FILE` variables.

#### Scenario: Deploying with secrets present

- **WHEN** the stack is deployed on a swarm where the named secrets exist
- **THEN** each service reads its credential from `/run/secrets/` at startup
- **AND** no credential value appears in the stack file or in `docker stack config` output

#### Scenario: Local development is unaffected

- **WHEN** the development stack runs under `docker compose`, which sets no `*_FILE` variables
- **THEN** the explicitly set environment variables are used unchanged

### Requirement: Application state survives service restarts

Data written by PostgreSQL and Redis SHALL persist across service restarts, task
rescheduling, and stack redeployment.

#### Scenario: Redeploying the stack

- **WHEN** the stack is redeployed or a datastore task is rescheduled onto its node
- **THEN** previously written data is still present
- **AND** persistence is backed by a host path, not by container-local storage

#### Scenario: Datastores stay on their data

- **WHEN** a datastore service is scheduled
- **THEN** a placement constraint pins it to the node holding its data

### Requirement: Services report their health to Swarm

Every service SHALL define a healthcheck, so Swarm can detect failed tasks and Traefik can
route only to healthy replicas.

#### Scenario: An unhealthy task

- **WHEN** a service's healthcheck fails repeatedly
- **THEN** Swarm marks the task unhealthy and replaces it
- **AND** traffic is not routed to it in the meantime

#### Scenario: Slow first start

- **WHEN** a service needs time to initialise before it can answer
- **THEN** its healthcheck allows a start period before counting failures

### Requirement: Resource consumption is bounded

Every service SHALL declare CPU and memory limits and reservations, so one service cannot
starve the rest of the Swarm.

#### Scenario: Scheduling a service

- **WHEN** Swarm schedules a service's task
- **THEN** the task is placed only where its reservation can be satisfied
- **AND** the running container cannot exceed its declared limit

### Requirement: Configuration is supplied without rebuilding images

Runtime configuration — database connection, Redis URLs, Django host and cookie settings,
and external API keys — SHALL be supplied to services as environment configuration in the
stack file, so changing it requires no image rebuild.

#### Scenario: Changing a setting

- **WHEN** an operator edits a value in the stack file and redeploys
- **THEN** the new value takes effect
- **AND** no image is rebuilt or re-pushed

#### Scenario: Build-time configuration is distinguished

- **WHEN** a value must be present while the frontend is built rather than when it runs
- **THEN** it is supplied as a build argument
- **AND** the stack file does not rely on setting it at runtime

