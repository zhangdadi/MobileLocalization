import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import main


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        root = Path(self.storage.name)
        storage_patch = patch.object(main, "STORAGE_DIR", root)
        backup_patch = patch.object(main, "OLD_ENGLISH_DIR", root / "_old_english")
        storage_patch.start()
        backup_patch.start()
        self.addCleanup(storage_patch.stop)
        self.addCleanup(backup_patch.stop)
        for platform in main.LANGUAGE_DIR_MAP:
            for language in main.LANGUAGES:
                main.get_language_root(platform, language).mkdir(parents=True)
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)
        token = main.create_access_token(next(iter(main.AUTH_USERS)))
        self.client.headers["Authorization"] = f"Bearer {token}"

    def upload(self, platform, language, content):
        filename = main.PREFERRED_FILE_NAME[platform]
        response = self.client.post(
            "/api/upload",
            data={"platform": platform, "language": language},
            files={"upload_file": (filename, content.encode("utf-8"))},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["relative_path"]

    def table(self, platform):
        response = self.client.get("/api/editor-table", params={"platform": platform})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_ios_inline_context_and_escaped_values(self):
        content = r'''/* English file header */
"cancel" = "Cancel";//通用弹窗的取消按钮。
"link" = "https://example.com/a//b"; //链接入口
"quoted" = "Say \"Hello\"; // now"; //带引号的提示
"plain" = "No comment";
'''
        parsed = main.parse_ios_strings(content)
        self.assertEqual(len(parsed), 4)
        self.assertEqual(parsed["link"], "https://example.com/a//b")
        self.assertEqual(parsed["quoted"], 'Say "Hello"; // now')
        self.assertEqual(main.parse_usage_contexts("ios", content)["cancel"], "通用弹窗的取消按钮。")

    def test_portuguese_upload_save_sync_and_readonly_context(self):
        self.upload("ios", "en", '"cancel" = "Cancel";//通用弹窗的取消按钮。\n')
        self.upload("android", "en", '<resources><string name="dismiss">Cancel</string></resources>')
        for platform in ("ios", "android"):
            for language in ("ar", "tr", "pt-BR"):
                key = "cancel" if platform == "ios" else "dismiss"
                rows = [{"key": key, language: "Original"}]
                self.upload(platform, language, main.serialize_translation_rows(platform, rows, language))

        table = self.table("ios")
        self.assertTrue(table["uploaded_languages"]["pt-BR"])
        self.assertEqual(table["rows"][0]["usage_context"], "通用弹窗的取消按钮。")
        table["rows"][0]["pt-BR"] = "Cancelar"
        table["rows"][0]["usage_context"] = "不允许写入的场景"
        response = self.client.post("/api/editor-table", json={
            "platform": "ios", "relative_path": table["relative_path"], "rows": table["rows"],
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("pt-BR", response.json()["saved_languages"])
        self.assertEqual(self.table("android")["rows"][0]["pt-BR"], "Cancelar")
        self.assertEqual(self.table("ios")["rows"][0]["usage_context"], "通用弹窗的取消按钮。")

        # Sync also works in the reverse direction, without removing English notes.
        android = self.table("android")
        android["rows"][0]["pt-BR"] = "Fechar"
        response = self.client.post("/api/editor-table", json={
            "platform": "android", "relative_path": android["relative_path"], "rows": android["rows"],
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.table("ios")["rows"][0]["pt-BR"], "Fechar")
        self.assertEqual(self.table("ios")["rows"][0]["usage_context"], "通用弹窗的取消按钮。")
        portuguese_file = main.get_language_root("ios", "pt-BR") / "Localizable.strings"
        self.assertNotIn("//", portuguese_file.read_text())

    def test_missing_portuguese_file_is_not_created_by_editor(self):
        self.assertFalse(self.table("ios")["uploaded_languages"]["pt-BR"])
        self.upload("ios", "en", '"cancel" = "Cancel"; //取消按钮\n')
        table = self.table("ios")
        table["rows"][0]["pt-BR"] = "Cancelar"
        response = self.client.post("/api/editor-table", json={
            "platform": "ios", "relative_path": table["relative_path"], "rows": table["rows"],
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("pt-BR", response.json()["skipped_languages"])
        self.assertEqual(main.list_relative_files("ios", "pt-BR"), [])

    def test_append_retains_english_context_without_copying_it_to_translations(self):
        path = self.upload("ios", "en", '"cancel" = "Cancel"; //取消按钮\n')
        self.upload("ios", "pt-BR", '"cancel" = "Cancelar";\n')
        response = self.client.post("/api/file-content/append", json={
            "platform": "ios", "language": "en", "relative_path": path,
            "content": '"send" = "Send"; //发送消息按钮',
        })
        self.assertEqual(response.status_code, 200, response.text)
        rows = {row["key"]: row for row in self.table("ios")["rows"]}
        self.assertEqual(rows["send"]["usage_context"], "发送消息按钮")
        translated = main.get_language_root("ios", "pt-BR") / path
        self.assertNotIn("//", translated.read_text())


if __name__ == "__main__":
    unittest.main()
