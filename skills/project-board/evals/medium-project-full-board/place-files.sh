#!/usr/bin/env bash
# Builds the test project in the current folder: three dated commits (editions of the plan and
# the roadmap, session numbers in the messages) and one new file left uncommitted.
set -eu
here="$(dirname "$0")/files"
git init -q
c() { GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git -c user.name=test -c user.email=test@localhost commit -q -m "$2"; }
cp -R "$here/1/." . && git add -A && c "2026-10-17T10:00:00+09:00" "RECIPE: rules, plan and roadmap edition 1"
cp -R "$here/2/." . && git add -A && c "2026-10-19T18:00:00+09:00" "RECIPE S1 S2 done: contents and photo plan, roadmap edition 2"
cp -R "$here/3/." . && git add -A && c "2026-10-21T21:00:00+09:00" "RECIPE S3 first chapter draft, S4 started"
cp -R "$here/work/." .
