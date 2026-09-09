"""Config precedence and the three-layer write gate.

The gate matters more than anything else in this repo: an agent calls this CLI
autonomously, and a write is public and attributable.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from reddit_cli import cli, config as config_module
from reddit_cli.config import Config, ConfigError, load, save_tokens

FULL = dict(client_id="id", client_secret="secret", refresh_token="token")


class TestWriteGate(unittest.TestCase):
    def test_blocked_when_allow_write_false(self):
        ok, why = Config(**FULL, allow_write=False, granted_scopes=["submit"]).can_write()
        self.assertFalse(ok)
        self.assertIn("allow_write", why)

    def test_blocked_when_token_is_read_only(self):
        ok, why = Config(**FULL, allow_write=True, granted_scopes=["read", "identity"]).can_write()
        self.assertFalse(ok)
        self.assertIn("read-only", why)

    def test_open_when_both_layers_pass(self):
        ok, why = Config(**FULL, allow_write=True, granted_scopes=["read", "submit"]).can_write()
        self.assertTrue(ok)
        self.assertEqual(why, "")

    def test_cli_refuses_without_the_flag_even_when_config_allows(self):
        cfg = Config(**FULL, allow_write=True, granted_scopes=["submit"])
        args = mock.Mock(i_am_sure=False, subreddit="test", title="t", text="b")
        with self.assertRaises(ConfigError) as ctx:
            cli.cmd_post(args, cfg)
        self.assertIn("--i-am-sure", str(ctx.exception))

    def test_comment_refuses_without_the_flag(self):
        cfg = Config(**FULL, allow_write=True, granted_scopes=["submit"])
        args = mock.Mock(i_am_sure=False, parent="abc123", text="b")
        with self.assertRaises(ConfigError):
            cli.cmd_comment(args, cfg)


class TestConfigLoading(unittest.TestCase):
    def test_env_beats_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('[reddit]\nclient_id = "from_file"\n', encoding="utf-8")
            with mock.patch.dict("os.environ", {"REDDIT_CLIENT_ID": "from_env"}):
                self.assertEqual(load(path).client_id, "from_env")

    def test_missing_file_is_not_an_error(self):
        with TemporaryDirectory() as tmp:
            cfg = load(Path(tmp) / "nope.toml")
            self.assertIsNone(cfg.client_id)
            self.assertFalse(cfg.allow_write)

    def test_require_auth_points_at_the_right_next_step(self):
        with self.assertRaises(ConfigError) as ctx:
            Config(client_id="a", client_secret="b").require_auth()
        self.assertIn("reddit auth", str(ctx.exception))

        with self.assertRaises(ConfigError) as ctx:
            Config().require_auth()
        self.assertIn("prefs/apps", str(ctx.exception))

    def test_op_ref_only_consulted_when_value_absent(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                '[reddit]\nclient_secret = "direct"\n\n[reddit.op]\n'
                'client_secret_ref = "op://v/i/f"\n',
                encoding="utf-8",
            )
            with mock.patch.object(config_module, "_resolve_op_ref") as resolver:
                cfg = load(path)
            resolver.assert_not_called()
            self.assertEqual(cfg.client_secret, "direct")

    def test_save_tokens_round_trips_without_duplicating_keys(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                '[reddit]\nclient_id = "cid"\nclient_secret = "sec"\nallow_write = true\n',
                encoding="utf-8",
            )
            save_tokens("tok1", ["read"], path)
            save_tokens("tok2", ["read", "submit"], path)  # second run must not corrupt
            cfg = load(path)
            self.assertEqual(cfg.refresh_token, "tok2")
            self.assertEqual(cfg.client_id, "cid")
            self.assertTrue(cfg.allow_write)
            self.assertIn("submit", cfg.granted_scopes)

    def test_saved_config_is_not_world_readable(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            save_tokens("tok", ["read"], path)
            self.assertEqual(path.stat().st_mode & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
