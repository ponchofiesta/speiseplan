import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import download_pdfs
import speiseplan_service


class SpeiseplanServiceRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cache_file = speiseplan_service.CACHE_FILE
        speiseplan_service.CACHE_FILE = str(Path(self.temp_dir.name) / "speiseplan_cache.json")
        speiseplan_service._processing_events.clear()

    def tearDown(self):
        speiseplan_service.CACHE_FILE = self.original_cache_file
        speiseplan_service._processing_events.clear()
        self.temp_dir.cleanup()

    def test_failed_lookup_is_cached(self):
        download_calls = 0

        def fake_download_all_pdfs(target_kw=None):
            nonlocal download_calls
            download_calls += 1
            return {"found": 0, "downloaded": 0, "skipped": 0, "failed": 0, "pdfs": []}

        with patch("speiseplan_service.find_pdf_for_week", return_value=None), patch(
            "speiseplan_service.download_all_pdfs", side_effect=fake_download_all_pdfs
        ):
            first = speiseplan_service.get_speiseplan(14)
            second = speiseplan_service.get_speiseplan(14)

        self.assertIn("error", first)
        self.assertIn("error", second)
        self.assertEqual(download_calls, 1)

    def test_parallel_failed_requests_share_one_processing_run(self):
        download_calls = 0
        results = []

        def fake_download_all_pdfs(target_kw=None):
            nonlocal download_calls
            download_calls += 1
            time.sleep(0.1)
            return {"found": 0, "downloaded": 0, "skipped": 0, "failed": 0, "pdfs": []}

        def worker():
            results.append(speiseplan_service.get_speiseplan(14))

        with patch("speiseplan_service.find_pdf_for_week", return_value=None), patch(
            "speiseplan_service.download_all_pdfs", side_effect=fake_download_all_pdfs
        ):
            threads = [threading.Thread(target=worker) for _ in range(5)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(len(results), 5)
        self.assertTrue(all("error" in result for result in results))
        self.assertEqual(download_calls, 1)
        self.assertEqual(speiseplan_service._processing_events, {})


class DownloadPdfsRegressionTests(unittest.TestCase):
    def test_download_all_pdfs_closes_scraper_on_early_return(self):
        scraper = MagicMock()

        with patch("download_pdfs.create_session", return_value=scraper), patch(
            "download_pdfs.navigate_to_menuplaene", return_value="<html></html>"
        ), patch("download_pdfs.extract_pdf_links", return_value=[]):
            stats = download_pdfs.download_all_pdfs(target_kw=14)

        self.assertEqual(stats["found"], 0)
        scraper.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()