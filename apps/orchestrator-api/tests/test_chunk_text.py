import unittest

from orchestrator_api.modules.indexing.chunk_text import chunk_markdown, chunk_text, choose_chunks


class ChunkTextTests(unittest.TestCase):
    def test_splits_on_paragraphs_not_mid_word_when_possible(self):
        p1 = "Абзац про импорт пользователей. " * 20
        p2 = "Второй абзац про ошибки код E100. " * 20
        text = p1.strip() + "\n\n" + p2.strip()
        chunks = chunk_text(text, max_chars=500)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(c), 550)

    def test_markdown_splits_by_h2_with_heading(self):
        text = (
            "# Документ\n\n"
            "Вводный абзац.\n\n"
            "## Раздел A\n\n"
            "Текст раздела A.\n\n"
            "## Раздел B\n\n"
            "Текст раздела B."
        )
        chunks = chunk_markdown(text, max_chars=500)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(any(c.startswith("# Документ") and "## Раздел A" in c for c in chunks))
        self.assertTrue(any("## Раздел B" in c for c in chunks))
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-40:]
            self.assertFalse(chunks[i].startswith(prev_tail[:20]))

    def test_choose_chunks_uses_markdown_for_ai_flag(self):
        md = "# T\n\n## A\n\nfoo\n\n## B\n\nbar"
        parts = choose_chunks(md, file_format="md", ai_normalized=True)
        self.assertTrue(any("## A" in p for p in parts))


if __name__ == "__main__":
    unittest.main()
