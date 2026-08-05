#!/bin/sh
# Prepares the environment for a backend container, then execs the service command.
#
# All three backend services (web, celery worker, celery beat) share this image and
# therefore this script. What differs between them is supplied by the stack file:
# only the Django service sets DJANGO_MIGRATE_ON_START.
#
# Note: `docker exec` bypasses an ENTRYPOINT, so management commands must be run as
#   /app/deploy/entrypoint.sh python manage.py <command>
# otherwise none of the derivation below has happened.
set -e

# --- Redis ------------------------------------------------------------------
#
# The stack file supplies one REDIS_URL. Deriving the rest here keeps the same host
# and port from being repeated across three variables on three services, where they
# drift. Anything already set explicitly wins.

if [ -n "${REDIS_URL:-}" ]; then
    # Celery refuses a rediss:// broker without an explicit ssl_cert_reqs. Set
    # REDIS_SSL_CERT_REQS=none if the server's certificate does not validate.
    case "$REDIS_URL" in
        rediss://*)
            case "$REDIS_URL" in
                *ssl_cert_reqs=*) ;;
                *\?*) REDIS_URL="$REDIS_URL&ssl_cert_reqs=${REDIS_SSL_CERT_REQS:-required}" ;;
                *) REDIS_URL="$REDIS_URL?ssl_cert_reqs=${REDIS_SSL_CERT_REQS:-required}" ;;
            esac
            ;;
    esac

    # Give the result backend its own logical database so it cannot collide with
    # queued messages in the broker's.
    case "$REDIS_URL" in
        */0\?*) _result_url=$(printf '%s' "$REDIS_URL" | sed 's|/0?|/1?|') ;;
        */0) _result_url="${REDIS_URL%/0}/1" ;;
        *) _result_url="$REDIS_URL" ;;
    esac

    [ -z "${CELERY_BROKER_URL:-}" ] && export CELERY_BROKER_URL="$REDIS_URL"
    [ -z "${CELERY_RESULT_BACKEND:-}" ] && export CELERY_RESULT_BACKEND="$_result_url"
    [ -z "${DJANGO_CACHE_URL:-}" ] && export DJANGO_CACHE_URL="$REDIS_URL"
fi

# --- Wait for the database --------------------------------------------------
#
# Swarm has no depends_on. Without this, all three backend services crash-loop
# through their restart policy until Postgres accepts connections -- noisy, and slow
# to converge. Bounded so a genuinely unreachable database fails loudly instead of
# hanging a task forever in "starting".

_db_host="${POSTGRES_HOST:-db}"
_db_port="${POSTGRES_PORT:-5432}"
_wait="${POSTGRES_WAIT_SECONDS:-60}"
_waited=0

while ! python -c "
import socket, sys
try:
    socket.create_connection(('$_db_host', $_db_port), timeout=2).close()
except OSError:
    sys.exit(1)
" 2>/dev/null; do
    if [ "$_waited" -ge "$_wait" ]; then
        echo "entrypoint: $_db_host:$_db_port unreachable after ${_wait}s" >&2
        exit 1
    fi
    _waited=$((_waited + 2))
    sleep 2
done

# --- Migrations -------------------------------------------------------------
#
# Gated on an explicit variable, set only on the Django service. Celery worker and
# beat share this image; without the gate all three would migrate concurrently on
# every deploy and race each other.
#
# Deliberately NOT inferred from "$@" -- matching on the command string couples this
# to the exact CMD and fails silently the first time one is reworded, and a silent
# failure to migrate is far worse than a loud one.
#
# `set -e` makes a non-zero migrate exit abort before the exec below, so a failed
# migration fails the task rather than serving against a stale schema.

case "${DJANGO_MIGRATE_ON_START:-}" in
    1|true|True|TRUE|yes|on)
        echo "entrypoint: applying migrations"
        python manage.py migrate --noinput
        ;;
esac

exec "$@"
