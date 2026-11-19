#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plain_lint.py 시험. 돌리는 법: python3 test_plain_lint.py  (표준 라이브러리 unittest)

시험용 용어집과 예시 글은 fixtures/ 에 있다. 실제 프로젝트 용어집에 기대지 않는다.
훅 시험은 임시 폴더에 가짜 프로젝트를 만들고, HOME도 임시 폴더로 바꿔 돌린다(진짜 ~/.cache 를 건드리지 않음).
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "plain_lint.py")
FIX = os.path.join(HERE, "fixtures")
GLOSS = os.path.join(FIX, "GLOSSARY.md")

spec = importlib.util.spec_from_file_location("plain_lint", SCRIPT)
pl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pl)
RULES, ALLOWS, PROBLEMS = pl.load_glossary(GLOSS)


def read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


def words(text, kind="md"):
    hits, _ = pl.check_text(text, kind, RULES, ALLOWS)
    return [h[3] for h in hits]


class GlossaryTest(unittest.TestCase):
    def test_loads_rules_and_allows(self):
        self.assertEqual(PROBLEMS, [])
        self.assertGreaterEqual(len(RULES), 13)
        self.assertEqual(len(ALLOWS), 1)

    def test_real_project_glossary_if_present(self):
        # 이 스킬을 쓰는 프로젝트 용어집이 있으면, 문제 없이 읽히는지만 본다.
        real = os.environ.get("PLAIN_REAL_GLOSSARY")
        if not real or not os.path.isfile(real):
            self.skipTest("PLAIN_REAL_GLOSSARY 없음")
        rules, allows, problems = pl.load_glossary(real)
        self.assertEqual(problems, [])
        self.assertGreater(len(rules), 30)

    def test_bad_regex_row_is_reported_not_crash(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "G.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write("| 말 | 쉬운 뜻 | 검사가 세는 글자 |\n|---|---|---|\n| 깨진 줄 | 뜻 | `~K(` |\n| 좋은 줄 | 뜻 | `G1` |\n")
            rules, allows, problems = pl.load_glossary(p)
            self.assertEqual(len(problems), 1)
            self.assertEqual(len(rules), 1)
        finally:
            shutil.rmtree(d)


class BadTextWarns(unittest.TestCase):
    def test_goldset_sentence(self):
        w = words(read("bad_goldset.md"))
        for x in ["다름 칸", "K2", "기댄", "G1", "K4", "G2", "약해짐", "남은 가설", "살아남음"]:
            self.assertIn(x, w)
        # 괄호 안 (K2, K4, K5)는 세지 않으므로 K5는 없다
        self.assertNotIn("K5", w)
        self.assertEqual(w.count("K2"), 1)

    def test_root_cause_example(self):
        w = words(read("bad_rootcause.md"))
        for x in ["다름 칸", "K2", "기댄", "G1", "meta:", "like_count", "M:", "cut_rate"]:
            self.assertIn(x, w)

    def test_field_names(self):
        w = words(read("bad_fields.md"))
        self.assertEqual(w, ["no_special_reason", "card_summary", "recsql"])

    def test_session_memo(self):
        self.assertEqual(words(read("bad_session_memo.md")), ["S5b", "S5a", "S6", "s5b"])

    def test_specific_row_wins_over_general_row(self):
        hits, _ = pl.check_text("S5b 결과", "md", RULES, ALLOWS)
        self.assertEqual(len(hits), 1)
        self.assertIn("깊은 분석", hits[0][2].meaning)

    def test_page_visible_text_and_script_strings(self):
        w = words(read("bad_page.html"), "html")
        for x in ["다름 칸", "K2", "기댄", "G1", "약해짐", "S5b", "G2"]:
            self.assertIn(x, w)
        self.assertNotIn("K9", w)        # 한글 없는 스크립트 문자열
        self.assertNotIn("recsql", w)    # 문자열 안 <code>

    def test_korean_particle_after_code(self):
        self.assertEqual(words("K2가 크고 G1은 작다"), ["K2", "G1"])


class GoodTextQuiet(unittest.TestCase):
    def test_plain_rewrite(self):
        self.assertEqual(words(read("good_plain.md")), [])

    def test_code_marks_parens_raw_url_comment(self):
        self.assertEqual(words(read("good_code.md")), [])

    def test_good_page(self):
        self.assertEqual(words(read("good_page.html"), "html"), [])

    def test_near_misses(self):
        for s in ["K2O 분자", "4K2 화면", "AK2 소총", "K123", "다름이 없다", "S02 흐름"]:
            self.assertEqual(words(s), [], s)

    def test_allowlist(self):
        self.assertEqual(words("second_brain 저장소에 남겨요"), [])
        self.assertEqual(words("other_brain 저장소"), ["other_brain"])

    def test_account_handle_with_at_sign(self):
        self.assertEqual(words("@sample_creator_01 계정은 뺐어요"), [])
        self.assertEqual(words("sample_creator_01 계정은 뺐어요"), ["sample_creator_01"])
        # 점이 섞인 계정 이름도 @가 붙으면 통째로 세지 않는다
        self.assertEqual(words("@ai.design_sample, @may.one_sample 두 계정"), [])
        self.assertEqual(words("ai.design_sample 계정"), ["design_sample"])
        # 메일 주소의 @ 뒤는 계정이 아니지만, 세지 않아도 괜찮다(코드 이름 경고가 덜 나는 쪽)
        self.assertEqual(words("메일은 team@example.com"), [])


class Josa(unittest.TestCase):
    def test_josa(self):
        self.assertEqual(pl.josa("세션 메시지", "은", "는"), "는")
        self.assertEqual(pl.josa("새 세션 첫 지시문", "은", "는"), "은")
        self.assertEqual(pl.josa("마무리 상자 글", "을", "를"), "을")
        self.assertEqual(pl.josa("올린 페이지(page.html)", "은", "는"), "는")

    def test_messages_use_right_particle(self):
        g = pl.group_hits(*([pl.check_text("S5b", "md", RULES, ALLOWS)[0], "S5b", "S5b"]))
        self.assertIn("세션 메시지는", pl.build_message("세션 메시지", g, 1, "pre"))
        self.assertIn("세션 메시지를 이미", pl.build_message("세션 메시지", g, 1, "sent"))
        self.assertIn("첫 지시문은", pl.build_message("새 세션 첫 지시문", g, 1, "pre"))

    def test_unclosed_fence_hides_rest(self):
        self.assertEqual(words("설명\n```\nK2 G1\n"), [])

    def test_paren_does_not_cross_paragraph(self):
        self.assertEqual(words("열린 괄호 (설명\n\nK2 다음 문단"), ["K2"])


class LineNumbers(unittest.TestCase):
    def test_lines(self):
        text = "첫 줄\n둘째 줄 K2\n셋째\n넷째 G1"
        hits, masked = pl.check_text(text, "md", RULES, ALLOWS)
        groups = pl.group_hits(hits, text, masked)
        self.assertEqual([g["lines"] for g in groups], [[2], [4]])


# ---------------------------------------------------------------- 훅 시험

class HookBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.proj = os.path.join(self.tmp, "proj")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.proj, "docs", "reports"))
        os.makedirs(self.home)
        shutil.copy(GLOSS, os.path.join(self.proj, "docs", "GLOSSARY.md"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_hook(self, payload, proj=None, raw=None):
        env = dict(os.environ)
        env["HOME"] = self.home
        env["CLAUDE_PROJECT_DIR"] = proj or self.proj
        data = raw if raw is not None else json.dumps(payload, ensure_ascii=False)
        t0 = time.time()
        r = subprocess.run([sys.executable, SCRIPT, "--hook"], input=data.encode("utf-8"),
                           capture_output=True, env=env, timeout=30)
        self.elapsed = time.time() - t0
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        out = r.stdout.decode("utf-8").strip()
        return json.loads(out) if out else None

    def doc(self, rel, text):
        p = os.path.join(self.proj, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def assertNeverBlocks(self, out):
        if out is None:
            return
        self.assertNotIn("decision", out)
        hso = out.get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", hso)


class PostFileHook(HookBase):
    def payload(self, tool, ti):
        return {"hook_event_name": "PostToolUse", "tool_name": tool, "tool_input": ti,
                "session_id": "t1", "cwd": self.proj}

    def test_write_in_scope_warns_without_blocking(self):
        text = read("bad_goldset.md")
        p = self.doc("docs/reports/r.md", text)
        out = self.run_hook(self.payload("Write", {"file_path": p, "content": text}))
        self.assertIsNotNone(out)
        self.assertNeverBlocks(out)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("K2", ctx)
        self.assertIn("plain-words", ctx)
        self.assertIn("docs/reports/r.md", ctx)
        self.assertLess(self.elapsed, 5)

    def test_write_clean_is_quiet(self):
        text = read("good_plain.md")
        p = self.doc("docs/reports/ok.md", text)
        self.assertIsNone(self.run_hook(self.payload("Write", {"file_path": p, "content": text})))

    def test_root_status_and_claude_files_in_scope(self):
        for name in ["STATUS.md", "CLAUDE.md"]:
            p = self.doc(name, "S5b 하는 중")
            out = self.run_hook(self.payload("Write", {"file_path": p, "content": "S5b 하는 중"}))
            self.assertIsNotNone(out, name)

    def test_out_of_scope_paths_quiet(self):
        for rel in ["src/app.py", "docs/data.json", "docs/USER_NOTES.md", "docs/GLOSSARY.md",
                    "docs/archive/old.md", "team-repo/docs/x.md", "README.md"]:
            p = self.doc(rel, "K2 G1 S5b")
            self.assertIsNone(self.run_hook(self.payload("Write", {"file_path": p, "content": "K2 G1 S5b"})), rel)

    def test_no_glossary_project_quiet(self):
        other = os.path.join(self.tmp, "other")
        os.makedirs(os.path.join(other, "docs"))
        p = os.path.join(other, "docs", "r.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("K2 G1")
        self.assertIsNone(self.run_hook(self.payload("Write", {"file_path": p, "content": "K2 G1"}), proj=other))

    def test_edit_checks_only_new_text(self):
        old_bad = "예전 줄: 다름 칸 K2에 기댄 G1\n"
        p = self.doc("docs/reports/e.md", old_bad + "새 줄: 근거가 약했어요\n")
        out = self.run_hook(self.payload("Edit", {"file_path": p, "old_string": "x", "new_string": "새 줄: 근거가 약했어요"}))
        self.assertIsNone(out)
        self.doc("docs/reports/e.md", old_bad + "새 줄: S5a가 넣어요\n")
        out = self.run_hook(self.payload("Edit", {"file_path": p, "old_string": "x", "new_string": "새 줄: S5a가 넣어요"}))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("S5a", ctx)
        self.assertNotIn("K2", ctx)

    def test_edit_inside_code_block_of_file_quiet(self):
        p = self.doc("docs/reports/c.md", "설명\n\n```\nS5b K2\n```\n")
        self.assertIsNone(self.run_hook(self.payload("Edit", {"file_path": p, "old_string": "x", "new_string": "S5b K2"})))

    def test_multiedit(self):
        p = self.doc("docs/reports/m.md", "하나 G1\n둘 깨끗\n")
        out = self.run_hook(self.payload("MultiEdit", {"file_path": p, "edits": [
            {"old_string": "a", "new_string": "하나 G1"}, {"old_string": "b", "new_string": "둘 깨끗"}]}))
        self.assertIn("G1", out["hookSpecificOutput"]["additionalContext"])

    def test_html_file_edit_in_script_string(self):
        page = read("bad_page.html")
        p = self.doc("docs/reports/p.html", page)
        out = self.run_hook(self.payload("Edit", {"file_path": p, "old_string": "x",
                                                   "new_string": 'title:"S5b 결과를 볼까"'}))
        self.assertIn("S5b", out["hookSpecificOutput"]["additionalContext"])


class PostPageHook(HookBase):
    def test_artifact_publish_warns(self):
        page = os.path.join(self.tmp, "scratch_page.html")   # 프로젝트 밖(작업 임시 폴더)이어도 본다
        shutil.copy(os.path.join(FIX, "bad_page.html"), page)
        out = self.run_hook({"hook_event_name": "PostToolUse", "tool_name": "Artifact",
                             "tool_input": {"file_path": page, "icon": "x"}, "session_id": "t1", "cwd": self.proj})
        self.assertNeverBlocks(out)
        self.assertIn("G2", out["hookSpecificOutput"]["additionalContext"])

    def test_artifact_other_actions_quiet(self):
        page = os.path.join(self.tmp, "p.html")
        shutil.copy(os.path.join(FIX, "bad_page.html"), page)
        for ti in [{"action": "read", "url": "u"}, {"action": "publish", "file_path": page, "asset": True, "url": "u"}]:
            self.assertIsNone(self.run_hook({"hook_event_name": "PostToolUse", "tool_name": "Artifact",
                                             "tool_input": ti, "session_id": "t1", "cwd": self.proj}))

    def test_good_page_quiet(self):
        page = os.path.join(self.tmp, "g.html")
        shutil.copy(os.path.join(FIX, "good_page.html"), page)
        self.assertIsNone(self.run_hook({"hook_event_name": "PostToolUse", "tool_name": "Artifact",
                                         "tool_input": {"file_path": page}, "session_id": "t1", "cwd": self.proj}))


class SendHooks(HookBase):
    WRAP = "mcp__ccd_turn__wrap_up"

    def pre(self, ti, tool=None, session="s1"):
        return self.run_hook({"hook_event_name": "PreToolUse", "tool_name": tool or self.WRAP,
                              "tool_input": ti, "session_id": session, "cwd": self.proj})

    def test_deny_once_then_let_through(self):
        bad = {"recap": "S5b가 K2 결과를 냈어요.", "ask": "다음은?"}
        first = self.pre(bad)
        hso = first["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertIn("S5b", hso["permissionDecisionReason"])
        self.assertIsNone(self.pre(bad))              # 다시 보내면 통과
        self.assertEqual(self.pre(bad)["hookSpecificOutput"]["permissionDecision"], "deny")  # 다음 글은 다시 한 번

    def test_clean_send_passes_and_clears_state(self):
        self.assertEqual(self.pre({"recap": "G1 확인"})["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIsNone(self.pre({"recap": "짐작 하나를 확인했어요."}))
        # 깨끗한 글이 상태를 지웠으니, 다음 어려운 글은 다시 한 번 멈춘다
        self.assertEqual(self.pre({"recap": "G1 확인"})["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_sessions_and_tools_are_separate(self):
        bad = {"recap": "S5b"}
        self.assertIsNotNone(self.pre(bad, session="a"))
        self.assertIsNotNone(self.pre(bad, session="b"))
        self.assertIsNotNone(self.pre({"message": "S5b"}, tool="SendMessage", session="a"))

    def test_start_session_prompt_and_background(self):
        out = self.pre({"title": "정리", "prompt": "깨끗한 글", "background": "다름 칸을 다시 봐"},
                       tool="mcp__ccd_session__start_session")
        self.assertIn("다름 칸", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_old_deny_expires(self):
        self.pre({"recap": "S5b"})
        # 상태 파일 시간을 11분 전으로 돌린다
        cache = os.path.join(self.home, ".cache", "plain-words")
        for name in os.listdir(cache):
            if name.startswith("deny-"):
                p = os.path.join(cache, name)
                with open(p, "w", encoding="utf-8") as f:
                    json.dump({"t": time.time() - 660}, f)
        self.assertIsNotNone(self.pre({"recap": "S5b"}))

    def test_post_send_warns_only(self):
        out = self.run_hook({"hook_event_name": "PostToolUse", "tool_name": "SendMessage",
                             "tool_input": {"to": "x", "message": "S5b 끝났어"}, "session_id": "s1", "cwd": self.proj})
        self.assertNeverBlocks(out)
        self.assertIn("이미 보냈", out["hookSpecificOutput"]["additionalContext"])

    def test_no_glossary_no_deny(self):
        other = os.path.join(self.tmp, "other")
        os.makedirs(other)
        out = self.run_hook({"hook_event_name": "PreToolUse", "tool_name": self.WRAP,
                             "tool_input": {"recap": "S5b"}, "session_id": "s1", "cwd": other}, proj=other)
        self.assertIsNone(out)


class Robustness(HookBase):
    def test_garbage_input(self):
        for raw in ["", "not json", "[1,2]", "{\"tool_input\": 3}", "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":7}}"]:
            self.assertIsNone(self.run_hook(None, raw=raw), raw)

    def test_error_is_logged_and_exit_zero(self):
        with open(os.path.join(self.proj, "docs", "GLOSSARY.md"), "wb") as f:
            f.write(b"\xff\xfe broken | `~K(` |\n")
        p = self.doc("docs/reports/r.md", "K2")
        out = self.run_hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                             "tool_input": {"file_path": p, "content": "K2"}, "session_id": "t", "cwd": self.proj})
        self.assertNeverBlocks(out)

    def test_large_file_is_fast(self):
        text = ("보통 문장이에요. K2와 G1, `code_name`, (S5b) 그리고 다름 칸.\n" * 6000)
        p = self.doc("docs/reports/big.md", text)
        out = self.run_hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                             "tool_input": {"file_path": p, "content": text}, "session_id": "t", "cwd": self.proj})
        self.assertIsNotNone(out)
        self.assertLess(len(out["hookSpecificOutput"]["additionalContext"]), 10000)
        self.assertLess(self.elapsed, 10)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, timeout=30)

    def test_exit_codes(self):
        self.assertEqual(self.run_cli("--glossary", GLOSS, os.path.join(FIX, "bad_fields.md")).returncode, 1)
        self.assertEqual(self.run_cli("--glossary", GLOSS, os.path.join(FIX, "good_plain.md")).returncode, 0)
        self.assertEqual(self.run_cli("--glossary", GLOSS, "--text", "G1 확인").returncode, 1)
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "x.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write("K2")
            self.assertEqual(self.run_cli(p).returncode, 2)   # 용어집을 못 찾음
        finally:
            shutil.rmtree(d)

    def test_json_output(self):
        r = self.run_cli("--glossary", GLOSS, "--json", os.path.join(FIX, "bad_session_memo.md"))
        data = json.loads(r.stdout.decode("utf-8"))
        self.assertEqual([d["word"] for d in data], ["S5b", "S5a", "S6", "s5b"])


class StopHook(HookBase):
    def stop(self, msg, active=False, proj=None):
        return self.run_hook({"hook_event_name": "Stop", "session_id": "st1", "cwd": proj or self.proj,
                              "stop_hook_active": active, "last_assistant_message": msg}, proj=proj)

    def test_blocks_once_with_reason(self):
        out = self.stop("S5b 세션이 K2 결과를 냈어요. 다음은 G1을 봐요.")
        self.assertEqual(out["decision"], "block")
        for w in ("S5b", "K2", "G1", "다시 쓰세요"):
            self.assertIn(w, out["reason"])

    def test_rewritten_answer_passes(self):
        self.assertIsNone(self.stop("S5b 세션이 K2 결과를 냈어요.", active=True))

    def test_clean_answer_passes(self):
        self.assertIsNone(self.stop("깊은 분석 세션이 첫 장면 결과를 냈어요. 브랜치에 커밋했고 push는 안 했어요."))

    def test_code_and_parens_are_not_counted(self):
        self.assertIsNone(self.stop("첫 장면(K2)을 봤어요. 명령은 `python3 run.py --s5b` 예요.\n```\nS5b K2\n```"))

    def test_no_glossary_project_passes(self):
        other = os.path.join(self.tmp, "other")
        os.makedirs(other)
        self.assertIsNone(self.stop("S5b 세션이 K2 결과를 냈어요.", proj=other))

    def test_empty_or_missing_message_passes(self):
        self.assertIsNone(self.stop(""))
        self.assertIsNone(self.run_hook({"hook_event_name": "Stop", "cwd": self.proj}))


class HandOffSend(HookBase):
    def test_hand_off_remaining_plan_is_checked(self):
        out = self.run_hook({"hook_event_name": "PreToolUse", "tool_name": "mcp__ccd_session__hand_off_to_session",
                             "tool_input": {"title": "정리 넘기기", "remaining_plan": "S5b 결과를 K2 기준으로 고친다"},
                             "session_id": "h1", "cwd": self.proj})
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertIn("세션 넘기기 지시문", hso["permissionDecisionReason"])


def make_pptx(path, slides):
    """slides: [(슬라이드 글 줄들, 메모 줄들)] — 글자만 든 아주 작은 pptx."""
    import zipfile

    def paras(lines):
        return "".join("<a:p><a:r><a:t>%s</a:t></a:r></a:p>" % l.replace("&", "&amp;").replace("<", "&lt;") for l in lines)
    ns = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        for i, (body, notes) in enumerate(slides, 1):
            z.writestr("ppt/slides/slide%d.xml" % i,
                       "<p:sld %s><p:cSld><p:spTree><p:sp><p:txBody>%s</p:txBody></p:sp></p:spTree></p:cSld></p:sld>" % (ns, paras(body)))
            if notes:
                z.writestr("ppt/notesSlides/notesSlide%d.xml" % i,
                           "<p:notes %s><p:cSld><p:spTree><p:sp><p:txBody>%s%s</p:txBody></p:sp></p:spTree></p:cSld></p:notes>"
                           % (ns, paras(notes), paras([str(i)])))


def make_epub(path, chapters):
    import zipfile
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml",
                   '<container><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>')
        items = "".join('<item id="c%d" href="c%d.xhtml" media-type="application/xhtml+xml"/>' % (i, i) for i in range(len(chapters)))
        spine = "".join('<itemref idref="c%d"/>' % i for i in reversed(range(len(chapters))))  # 읽는 순서를 거꾸로
        z.writestr("OEBPS/content.opf", "<package><manifest>%s</manifest><spine>%s</spine></package>" % (items, spine))
        for i, html in enumerate(chapters):
            z.writestr("OEBPS/c%d.xhtml" % i, "<html><head><title>S9z</title></head><body>%s</body></html>" % html)


class CodesOnly(unittest.TestCase):
    INTERNAL = ["S5b", "K2", "G1", "no_special_reason", "card_summary", "docs/reports/2026-11-17_analysis.md", "B3a"]
    GENERAL = ["Apify", "Supabase", "API", "URL", "CTA", "Q1", "H1", "A4"]

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def found(self, path):
        secs = pl.load_visible(path)
        return [h[3] for _, _, m in secs for h in pl.find_code_hits(m)]

    def run_cli(self, *args):
        return subprocess.run([sys.executable, SCRIPT, "--codes-only"] + list(args), capture_output=True, timeout=30)

    def test_deck_script_finds_every_internal_name(self):
        w = self.found(os.path.join(FIX, "codes_deck.md"))
        for x in self.INTERNAL:
            self.assertIn(x, w)
        for x in self.GENERAL:
            self.assertNotIn(x, w)

    def test_parens_and_backticks_still_count(self):
        hits = [h[3] for h in pl.find_code_hits(pl.mask_visible_md("첫 장면(K2)과 `card_id` 칸"))]
        self.assertEqual(hits, ["K2", "card_id"])

    def test_not_paths(self):
        t = "and/or, TCP/IP, 24/7, 읽기/쓰기, 2026/11/19, https://example.com/a/b.md, @ai_design.studio"
        self.assertEqual([h[3] for h in pl.find_code_hits(pl.mask_visible_md(t))], [])

    def test_clean_page_quiet(self):
        self.assertEqual(self.found(os.path.join(FIX, "codes_clean.html")), [])

    def test_pptx_slides_and_notes(self):
        p = os.path.join(self.tmp, "deck.pptx")
        make_pptx(p, [(["Apify와 API로 모아요"], []), (["S5b가 만든 결과"], ["K2를 먼저 말한다"])])
        secs = pl.load_visible(p)
        labels = [lab for lab, _, _ in secs]
        self.assertEqual(labels, ["슬라이드 1", "슬라이드 2", "슬라이드 2 발표자 메모"])
        self.assertEqual(self.found(p), ["S5b", "K2"])
        r = self.run_cli(p)
        self.assertEqual(r.returncode, 1)
        self.assertIn("[슬라이드 2 발표자 메모]", r.stdout.decode("utf-8"))

    def test_epub_follows_spine_and_skips_head(self):
        p = os.path.join(self.tmp, "book.epub")
        make_epub(p, ["<p>첫 장: Supabase에 저장해요</p>", "<p>둘째 장: B3a 계획과 <code>no_flag</code></p>"])
        secs = pl.load_visible(p)
        self.assertEqual([lab for lab, _, _ in secs], ["장 c1.xhtml", "장 c0.xhtml"])
        self.assertEqual(self.found(p), ["B3a", "no_flag"])

    def test_cli_exit_codes(self):
        self.assertEqual(self.run_cli(os.path.join(FIX, "codes_deck.md")).returncode, 1)
        self.assertEqual(self.run_cli(os.path.join(FIX, "codes_clean.html")).returncode, 0)
        self.assertEqual(self.run_cli("--text", "API와 URL을 써요").returncode, 0)
        self.assertEqual(self.run_cli("--text", "S5b를 써요").returncode, 1)
        pdf = os.path.join(self.tmp, "x.pdf")
        with open(pdf, "wb") as f:
            f.write(b"%PDF-1.4")
        r = self.run_cli(pdf)
        self.assertEqual(r.returncode, 2)
        self.assertIn("PDF", r.stderr.decode("utf-8"))

    def test_no_glossary_needed(self):
        r = subprocess.run([sys.executable, SCRIPT, "--codes-only", os.path.join(FIX, "codes_deck.md")],
                           capture_output=True, timeout=30, cwd=self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("용어집", r.stderr.decode("utf-8"))

    def test_json(self):
        r = self.run_cli("--json", os.path.join(FIX, "codes_deck.md"))
        data = json.loads(r.stdout.decode("utf-8"))
        self.assertEqual(sorted(d["word"] for d in data), sorted(self.INTERNAL))


if __name__ == "__main__":
    unittest.main(verbosity=1)
