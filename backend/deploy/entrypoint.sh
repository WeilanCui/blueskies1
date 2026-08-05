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

# --- Secrets ----------------------------------------------------------------
#
# Swarm delivers secrets as files under /run/secrets/. FOO_FILE=/run/secrets/x exports
# FOO with that file's contents, which is the convention the postgres and redis images
# already use. Runs first so everything below (REDIS_URL included) can come from a secret.
#
# An explicitly set FOO wins, so the compose development flow -- which sets no *_FILE
# variables at all -- is untouched.

for _var in $(env | sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)_FILE=.*/\1/p'); do
    # The explicit value is checked first: with a stale FOO_FILE left in the environment,
    # reading the file would otherwise fail the task even though FOO says what to use.
    eval "_current=\${${_var}:-}"
    if [ -n "$_current" ]; then
        continue
    fi

    eval "_path=\${${_var}_FILE}"
    if [ ! -r "$_path" ]; then
        echo "entrypoint: ${_var}_FILE=$_path is not readable" >&2
        exit 1
    fi
    export "$_var=$(cat "$_path")"
done
unset _var _path _current

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
        *)
            # Only db 0 is split automatically. Anything else would need parsing an
            # arbitrary index, so say plainly that results and messages will share a db
            # rather than pretending the separation happened.
            _result_url="$REDIS_URL"
            echo "entrypoint: REDIS_URL does not end in /0; results will share the" \
                 "broker's database. Set CELERY_RESULT_BACKEND explicitly to separate them." >&2
            ;;
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

# A malformed override must fail the task, not run the loop forever: `[ 0 -ge abc ]`
# exits 2, which as an `if` condition is indistinguishable from "not yet expired".
#
# Prints the value with leading zeros removed, because shell arithmetic reads a leading
# zero as octal: `$((0300))` is 192 seconds, and `$((08))` is not a number at all.
_seconds() {
    case "$2" in
        ''|*[!0-9]*)
            echo "entrypoint: $1 must be a non-negative integer, got '$2'" >&2
            exit 1
            ;;
    esac
    printf '%s' "$2" | sed 's/^0*\([0-9]\)/\1/'
}

# A real connection, not a TCP handshake: Postgres accepts connections on the port
# well before it will serve SQL, and a bare port check lets `migrate` run into that
# window. connect_timeout keeps one probe from outliving the deadline below.
_db_ready() {
    python - <<'PY' 2>/dev/null
import os
import sys

import psycopg

# Defaults mirror backend/config/settings.py DATABASES["default"].
try:
    psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "blueskies"),
        user=os.environ.get("POSTGRES_USER", "blueskies"),
        password=os.environ.get("POSTGRES_PASSWORD", "blueskies"),
        connect_timeout=2,
    ).close()
except Exception:
    sys.exit(1)
PY
}

_db_host="${POSTGRES_HOST:-db}"
_db_port="${POSTGRES_PORT:-5432}"
_wait=$(_seconds POSTGRES_WAIT_SECONDS "${POSTGRES_WAIT_SECONDS:-60}") || exit 1

# A wall-clock deadline, not a per-iteration counter: each probe can itself burn up to
# its connect timeout, so counting only the sleeps overshoots the documented bound.
_deadline=$(($(date +%s) + _wait))

while ! _db_ready; do
    if [ "$(date +%s)" -ge "$_deadline" ]; then
        echo "entrypoint: $_db_host:$_db_port not accepting queries after ${_wait}s" >&2
        exit 1
    fi
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
    *)
        # Everything else waits for those migrations instead of racing them. Swarm
        # starts all four backend services at once, so without this barrier a worker
        # can pick up queued work and run it against the previous schema for as long
        # as `backend` takes to migrate.
        _mwait=$(_seconds MIGRATION_WAIT_SECONDS "${MIGRATION_WAIT_SECONDS:-300}") || exit 1
        _mdeadline=$(($(date +%s) + _mwait))

        while ! python manage.py migrate --check >/dev/null 2>&1; do
            if [ "$(date +%s)" -ge "$_mdeadline" ]; then
                echo "entrypoint: migrations still pending after ${_mwait}s" >&2
                exit 1
            fi
            echo "entrypoint: waiting for migrations to be applied"
            sleep 5
        done
        ;;
esac

exec "$@"
