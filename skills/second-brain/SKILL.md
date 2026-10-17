---
name: second-brain
description: 도하의 작업 방식 묶음(plan-first, session-handoff, lean-context, doc-hygiene, brain-compile)의 입구. 사용자가 second_brain·second-brain을 말할 때, 새 프로젝트를 시작할 때, 기존 프로젝트에 이 방식을 적용하거나 점검할 때 먼저 써서 어느 스킬을 쓸지 정한다.
---

# second-brain (입구)

> 판 2026-10-17 · 원본 `tthwaghtt/second_brain`(비공개) `skills/` · 출처: obra/superpowers, mattpocock/skills, planning-with-files(모두 MIT)와 second_brain 노트에서 골라 다듬음

목표는 두 가지입니다. **① 맥락을 오염시키지 않고 끝까지 완성도 있게 만든다. ② 필요한 것은 빠짐없이, 나머지는 읽지 않는다.** 이 스킬은 길 안내만 합니다. 실제 규칙은 아래 스킬에 있습니다.

## 1. 상황 → 스킬

| 상황 | 스킬 |
|---|---|
| 새 일·기능·프로젝트를 시작함. "바로 만들어 줘"라도 일이 여러 세션 크기임 | `plan-first` |
| 세션 시작, 새 세션으로 넘길지 판단, 세션 끝 정리 | `session-handoff` |
| 무엇을 얼마나 읽을지, 큰 문서·로그·코드 탐색, 하위 에이전트에 맡기기 | `lean-context` |
| 문서를 만들거나 고침, 결정이 바뀜, 파일·폴더를 옮김 | `doc-hygiene` |
| 사용자가 second_brain inbox 정리를 요청함 | `brain-compile` |

**지금 단계에 맞는 스킬 하나만 엽니다.** 다른 스킬은 그 단계가 실제로 왔을 때 엽니다. 예를 들어 기획 중에는 `plan-first`만 열고, 세션을 끝낼 때가 되면 그때 `session-handoff`를 엽니다. 미리 다 읽어 두면 그 내용이 이번 일 내내 맥락을 차지합니다. 순서는 보통 `plan-first` → (일하는 동안 필요할 때 `lean-context`, `doc-hygiene`) → `session-handoff`입니다.

## 2. 기존 프로젝트에 이 방식을 적용할 때

1. **읽기만 합니다:** 규칙 파일, 상태 문서, 폴더 나무(`find . -maxdepth 2 -not -path './.git*'`), 큰 문서는 장 목록만. 본문을 통째로 읽지 않습니다(`lean-context`).
2. **어긋난 곳을 표로 보고합니다:** 문제 / 어긋난 규칙(스킬과 장) / 고칠 안 / 깨질 위험. 이미 잘 된 것도 한 줄 적습니다.
3. **승인 받은 범위만 고칩니다.** 그대로 복사하지 말고 그 프로젝트에 맞게 바꾸고, 바꾼 이유를 그 프로젝트 규칙 파일에 한 줄 남깁니다.

## 3. 우선순위

사용자의 지금 지시 > 프로젝트의 CLAUDE.md > 이 스킬들. 프로젝트에 맞지 않는 규칙은 빼고, 왜 뺐는지 보고합니다.

## 4. 원본과 되돌려 쓰기

- 규칙이 모자라면 second_brain 원본을 엽니다: `INDEX.md`만 → 필요한 노트의 장 하나만(`lean-context` 6장).
- 세션 끝에 다른 프로젝트에도 통할 교훈이 생기면 `session-handoff` 5장대로 inbox에 한 줄 남깁니다.
