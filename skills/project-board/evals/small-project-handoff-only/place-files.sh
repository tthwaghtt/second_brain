#!/usr/bin/env bash
# Builds the small test project in the current folder with one commit.
set -eu
cp -R "$(dirname "$0")/files/." .
git init -q && git add -A
GIT_AUTHOR_DATE="2026-10-20T22:00:00+09:00" GIT_COMMITTER_DATE="2026-10-20T22:00:00+09:00" \
  git -c user.name=test -c user.email=test@localhost commit -q -m "NOTEBOOK: three notes"
