require_local_target() {
  if ! printf '%s\n' "$1" | grep -Eq '^https?://(localhost|127\.0\.0\.1|\[::1\])(:[0-9]+)?(/|$)'; then
    echo "Refusing non-loopback target; use localhost, 127.0.0.1, or [::1]." >&2
    return 2
  fi
}
