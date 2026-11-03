---
description: Layer 3 명세 검증 — ai-cli-mcp Cross-Critique 2-Round (debate + security framing). 다중 AI 적대적 검토.
argument-hint: "명세서 경로 (생략 시 가장 최근 명세서 자동 탐지)"
---

# /spec-review — 명세 설계 검증 (Layer 3 명세 Adversarial)

spec-docs에서 생성된 명세서의 설계 품질을 다중 AI 적대적 검토로 검증한다.
**검토 후 수정사항이 없을 때까지 반복한다.**

글로벌 3-Layer 매핑: 이 단계는 **Layer 3 (Adversarial Review)** — 명세 단계의 약점을 *적대적 framing*으로 노출. 패턴 B(Cross-Critique 2-Round)로 모델 간 상호 비판하여 echo chamber 회피. "검토해줘"가 아니라 "이 설계가 6개월 후 실패한다면 가장 가능성 높은 시나리오"로 묻는다.

> 도구: `mcp__ai-cli__run` 다중 PID 병렬 호출.
>
> **Graceful Degradation:** 3 PID(sonnet + gemini-2.5-flash + gpt-5.3-codex) 발사 후 실패 PID(예: codex vendor ENOENT)는 자동 제외. Round 2 cross-critique도 살아있는 답끼리만. 작업 안 멈춤. 2개 이상 실패 시 Main 보고 후 단순 검토로 폴백.

모든 출력은 **한국어**로 한다.

---

## Step 0: 프로젝트 컨텍스트 로드

`.claude/config/project-context.yaml` 있으면 → `rules_dir`, `agents_md_path`, `worker_extra_rules`, `project_blockers` 사용.
없으면 → `.claude/rules/*.md`, `AGENTS.md` 자동 감지하여 적용.

---

## Step 1: 명세서 로드

**🧰 도구 연동:** spec-docs 가 만든 `/codemap` 산출물(`docs/codemaps/<앱>.md`)이 있으면 Cross-Critique prompt 컨텍스트에 첨부 — 리뷰어가 실제 구조·계약 위에서 비판. (코드 미존재라 mx/ralph/verify 는 이 단계 무의미.)

1) 인자로 명세서 경로 주어지면 해당 파일 Read
2) 인자 없으면 `docs/` 또는 vault `specs/`에서 가장 최근 수정된 명세서 자동 탐지
3) 명세서 없으면 "먼저 /spec-docs를 실행하세요" 안내 후 종료

---

## 리뷰 워커 쓰기 금지 (Step 2~4 의 모든 ai-cli 호출 공통, 필수)

리뷰 워커는 파일 쓰기 권한이 있어서 "검토만" 시켜도 코드를 고칠 수 있다 (2026-09-10 실측 — 메모리 `ai-cli-worker-writes-during-review`).

1. **호출 전 기준선**: `git status --porcelain` 출력과 `git diff | shasum` 값을 저장한다.
2. **모든 리뷰 프롬프트 맨 앞에 고정 문구**: "⛔ 파일을 만들거나 수정·삭제하지 마라. 상태를 바꾸는 명령을 실행하지 마라. 판정과 근거(파일:줄)만 텍스트로 출력하라."
3. **각 `wait` 직후**: 같은 두 값을 다시 떠서 기준선과 비교한다.
   - 기준선에 없던 파일이 바뀌었거나 새로 생겼으면 → 워커가 만든 변경이다. 파일 목록을 사용자에게 알리고 되돌린다 (`git checkout -- <파일>`, 새 파일은 삭제).
   - 기준선에 이미 있던 파일의 diff 값이 달라졌으면 → Main 의 미커밋 작업과 섞여 자동으로 되돌릴 수 없다. **멈추고 사용자에게 보고**한다.
   - 지적 내용 자체는 결과에 기록으로 남긴다 (범위 밖이면 해당 Phase 로 넘긴다).
4. 예상 밖 변경을 정리하기 전에는 다음 Round 를 시작하지 않는다.

---

## Step 2: Cross-Critique Round 1 — Debate framing (필수, 병렬 3 PID)

명세서 전문을 prompt에 포함하여 3개 모델에 동시 호출. 각 모델은 *서로의 답을 모르는 채* 독립 의견 (blinded → anchoring bias 회피).

```
mcp__ai-cli__run × 3 PID 동시:
  - sonnet            (Claude 시각, 설계·전반)
  - gemini-2.5-flash  (Gemini 시각, 그라운딩·다른 분포)
  - gpt-5.3-codex     (Codex 시각, 코드 디테일)
workFolder=repo root, prompt에 명세서 본문 포함

→ wait([3 pids], timeout=180) → get_result 각각 → answer_A, answer_B, answer_C
```

**각 모델에 던지는 framing (반드시 적대적 — 부드러운 "검토해줘" 금지):**
- "이 명세대로 구현했을 때 6개월 후 가장 가능성 높은 실패 시나리오 3개"
- "이 Phase 분리가 잘못 잡혔다면 어디인가"
- "더 단순한 대안이 있는데 과설계 된 부분"
- 검토 관점: Canonical Terms 모호성, Phase Contract Allowed/Forbidden 누락, 배정(S/R) 합리성
- 프로젝트 패턴 일치성 (yaml의 `worker_extra_rules` 또는 `.claude/rules/*` 자동 감지)

---

## Step 3: Cross-Critique Round 2 — Mutual Critique (필수, 병렬 PID, 살아있는 답끼리)

Round 1의 답들을 *교차*로 모델들에게 보여주고 약점을 비판하게 한다.

```
mcp__ai-cli__run × {살아있는 PID 수} 동시 (각자 *다른 답*을 prompt에 포함):
  - sonnet  ← {answer_B, answer_C} 받고 "B와 C의 약점·놓친 점·반박 근거" → 비판 A'
  - gemini  ← {answer_A, answer_C} 받고 "A와 C의 약점·놓친 점·반박 근거" → 비판 B'
  - codex   ← {answer_A, answer_B} 받고 "A와 B의 약점·놓친 점·반박 근거" → 비판 C'
  (codex 실패면 2-way: sonnet ← {B}, gemini ← {A})

→ wait → get_result
```

**메타인지 강제 (특히 답이 수렴할 때):**
> "두 답이 같은 결론으로 수렴했다면 — 이것이 정답의 증거인가, 질문 framing의 bias인가? 비판하라."

이 round가 단순 병렬 대비 진짜 *debate* 효과를 만드는 핵심.

---

## Step 4: Security framing 추가 호출 (조건부, 병렬 PID — 별도 1 round)

**발동 조건 (둘 중 하나라도 충족 시):**
- 명세서 본문에 보안 관련 키워드 포함 (인증/권한/세션/토큰/PII/OWASP/암호/credential/cookie/CORS/XSS/SQL/injection 등)
- `project-context.yaml` 의 `project_blockers` 에 보안 항목 명시

조건 미충족 → 1줄 알림 후 스킵 ("보안 키워드 없음 — security framing 스킵") → Step 5로 진행.

명세 단계 보안 검토 — debate와는 framing이 달라 별도 호출.

```
mcp__ai-cli__run × 3 PID 동시 (security framing):
  - sonnet
  - gemini-2.5-flash
  - gpt-5.3-codex (보안 framing은 코드 디테일 강점이 가치 큼)
```

**Security framing prompt:**
- 인증/권한 변경이 포함되는가, 우회 가능성은
- 데이터 노출 위험 (PII, 토큰, 민감 정보)
- API/WebSocket 경로 변경 시 하위 호환성 / 인증 미들웨어 누락
- 민감 데이터 처리(저장·전송·로깅) OWASP 적합성
- 프로젝트 고유 BLOCKER (yaml `project_blockers` 있으면 인용)

Round 2 cross-critique은 security framing에는 적용 안 함.

---

## Step 5: Main 합성 (self-anchoring 방지)

총 외부 데이터 (Round 1 debate + Round 2 cross-critique + Step 4 security)를 Main이 합성한다.

**합성 순서 (필수):**
1. *외부 의견을 먼저 읽고 요약* — Main이 자기 첫 인상 형성 전에 다 흡수
2. 공통 약점 추출 (3+ 모델 동의 = high confidence)
3. 의견 갈리는 지점 (1~2 모델만 지적 = 검토 필요)
4. Main 자신의 시각과 *차이점*만 보고
5. **프로젝트 Anchor 강제** (글로벌 룰 `프로젝트 Anchor 원칙` 적용): 외부 답의 일반론 표현을 *명세서 안의 Phase 명·파일 경로·클래스명·API 경로·테이블*로 변환해 재기술. anchor 못 한 결론은 "코드에서 확인 안 됨 — 사용자 검토 필요" 명시. 결과 템플릿의 모든 약점·BLOCKER 항목에 적용.
   - ❌ "Phase boundary가 약함" → ✅ "`socket.gateway.ts:140`이 Phase 2(emit 분리) AC와 Phase 3(persistence) AC 양쪽에 걸침 — 명세 §Phase 2에 파일 귀속 명시 필요"

**평가 기준 (보조):**
| 검토 기준 | 확인 항목 |
|----------|----------|
| 프로젝트 컨벤션 | `.claude/rules/*` 또는 yaml `worker_extra_rules` 준수 |
| 정석적 설계 | 프레임워크·언어 표준 패턴 (NestJS/Django/React 등 — 프로젝트별 다름) |
| 과설계 기피 | Phase 세분화 과잉, 불필요한 추상화 |
| 명세 목적 달성 | 요구사항 커버리지, 누락 |
| 베스트 프랙티스 | 관심사 분리, 확장성 |

---

## Step 6: 결과 제시

```
━━━ 설계 검증 결과 ━━━

명세서: {경로}

Cross-Critique (debate framing):
  Round 1 — sonnet/gemini/codex 독립 의견 요약
  Round 2 — 교차 비판으로 노출된 약점

Security framing:
  - [모델별 우려 사항]

공통 약점 (high confidence, 3+ 모델 동의):
  1. ...

의견 갈리는 지점:
  1. ...

수정 필요:
  [BLOCKER] ...
  [WARNING] ...

수정 불필요:
  → PASS: 설계 검증 완료. /spec-run 으로 진행 가능.
```

---

## Step 7: 수정 반복 (국소 검증 우선)

수정 필요 사항이 있으면:
1. 사용자에게 제시 → 확인 후 명세서 수정
2. **국소 재검증 (기본)**: 수정된 *해당 항목·섹션*만 좁혀서 다시 던짐. 풀 사이클 재호출 금지.
   - BLOCKER 1건 → sonnet 단독 검증 (1 PID)
   - BLOCKER 2~3건 또는 cross-impact 우려 → 2~3 PID 병렬 (cross-critique 생략)
3. **풀 사이클 재호출 (예외)**: 명세서가 *대규모 재작성* (>30% 변경) 또는 Phase 구조 자체가 바뀐 경우에만 → Step 2~6 전체 재실행
4. BLOCKER 0건 + WARNING 0건(또는 사용자 무시 확인) 될 때까지 반복

$ARGUMENTS
