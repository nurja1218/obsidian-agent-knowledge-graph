#!/usr/bin/env bash
# commit-msg 가드 — AI 공동저자/생성 문구가 커밋 메시지에 들어가면 커밋을 거부한다.
#
# 배경(2026-09-04): 세션 지시("Co-Authored-By 를 붙여라")가 프로젝트 규칙
# (팀 레포 CLAUDE.md §커밋 "AI 문구/Co-Authored-By/이모지 금지")과 충돌했고,
# 그 세션이 지시를 따라 14개 커밋에 붙였다. 사람 판단 없이 규칙이 뒤집히면 안 되므로
# **도구 층에서 거부**한다.
#
# 우회: AI_ATTR_OK=1 (의도적으로 넣어야 할 때만)
set -uo pipefail
[ "${AI_ATTR_OK:-0}" = "1" ] && exit 0

MSG_FILE="${1:-}"
[ -n "$MSG_FILE" ] && [ -f "$MSG_FILE" ] || exit 0

# 주석(#) 줄은 제외하고 검사
BODY=$(grep -v '^#' "$MSG_FILE" 2>/dev/null || true)

HIT=$(printf '%s\n' "$BODY" | grep -inE \
  'co-authored-by:[[:space:]]*(claude|anthropic|copilot|cursor|gpt|codex|gemini)|noreply@anthropic\.com|generated with \[?claude|🤖 generated with' \
  || true)

if [ -n "$HIT" ]; then
  echo "⛔ 커밋 거부 — AI 공동저자/생성 문구가 커밋 메시지에 있습니다." >&2
  echo "$HIT" | sed 's/^/   /' >&2
  echo "" >&2
  echo "   프로젝트 규칙: CLAUDE.md §커밋 — 'AI 문구/Co-Authored-By/이모지 금지'" >&2
  echo "   해당 줄을 지우고 다시 커밋하세요. (의도적 예외: AI_ATTR_OK=1)" >&2
  exit 1
fi
exit 0
