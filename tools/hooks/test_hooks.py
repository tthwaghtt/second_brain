#!/usr/bin/env python3
"""tools/hooks 시험: python3 tools/hooks/test_hooks.py (HOME을 임시 폴더로 바꿔 돌림)"""
import json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, payload, home, *args):
    env = dict(os.environ, HOME=home)
    r = subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args),
                       input=json.dumps(payload, ensure_ascii=False).encode(), capture_output=True, env=env, timeout=20)
    assert r.returncode == 0, r.stderr
    out = r.stdout.decode().strip()
    return json.loads(out) if out else None


class LoginWall(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.home)

    def post(self, tool, resp, ti=None, sid="s1"):
        return run("login_wall_hint.py", {"hook_event_name": "PostToolUse", "tool_name": tool, "session_id": sid,
                                          "tool_input": ti or {"url": "https://www.notion.so/team/page"},
                                          "tool_response": resp}, self.home)

    def test_short_login_page_hints(self):
        out = self.post("WebFetch", "Notion\nLog in\nContinue with Google\nEmail")
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("[로그인 화면]", ctx)
        self.assertIn("www.notion.so", ctx)
        self.assertIn("Aside", ctx)

    def test_korean_and_status_codes(self):
        self.assertIsNotNone(self.post("mcp__Claude_Browser__get_page_text", {"text": "로그인이 필요합니다"}, sid="a"))
        self.assertIsNotNone(self.post("WebFetch", "Request failed with status code 403", sid="b"))
        self.assertIsNotNone(self.post("mcp__claude-in-chrome__read_page", [{"type": "text", "text": "401 Unauthorized"}], sid="c"))

    def test_long_article_about_login_is_quiet(self):
        body = "이 글은 서비스의 로그인 흐름을 설명합니다. " + ("본문 문장입니다. " * 600)
        self.assertIsNone(self.post("WebFetch", body))

    def test_long_page_with_password_field_hints(self):
        body = ("메뉴 " * 2500) + " Sign in  Password  Forgot password?"
        self.assertIsNotNone(self.post("WebFetch", body))

    def test_normal_page_and_other_tools_quiet(self):
        self.assertIsNone(self.post("WebFetch", "Supabase docs: getting started with tables"))
        self.assertIsNone(self.post("Read", "Log in"))
        self.assertIsNone(self.post("Artifact", "Log in", ti={"action": "publish", "file_path": "x.html"}))
        self.assertIsNotNone(self.post("Artifact", "Log in", ti={"action": "read", "url": "https://claude.ai/artifact/x"}))

    def test_once_per_host_per_session(self):
        self.assertIsNotNone(self.post("WebFetch", "Log in"))
        self.assertIsNone(self.post("WebFetch", "Log in"))
        self.assertIsNotNone(self.post("WebFetch", "Log in", sid="other"))

    def test_garbage_is_silent(self):
        env = dict(os.environ, HOME=self.home)
        r = subprocess.run([sys.executable, os.path.join(HERE, "login_wall_hint.py")], input=b"{not json",
                           capture_output=True, env=env)
        self.assertEqual((r.returncode, r.stdout), (0, b""))


class KoreanPrompt(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.home)

    def test_ask_line_on_every_prompt(self):
        for prompt in ("이거 고쳐 줘", "fix this"):
            out = run("korean_reply.py", {"prompt": prompt, "session_id": "k"}, self.home, "prompt")
            self.assertIn("질문 팝업(AskUserQuestion)", out["hookSpecificOutput"]["additionalContext"])

    def test_stop_blocks_english_once(self):
        run("korean_reply.py", {"prompt": "보고해 줘", "session_id": "k2"}, self.home, "prompt")
        msg = "I finished the task and updated the files. Everything passes now and nothing else remains."
        out = run("korean_reply.py", {"session_id": "k2", "last_assistant_message": msg}, self.home, "stop")
        self.assertEqual(out["decision"], "block")
        self.assertIsNone(run("korean_reply.py", {"session_id": "k2", "last_assistant_message": msg,
                                                  "stop_hook_active": True}, self.home, "stop"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
