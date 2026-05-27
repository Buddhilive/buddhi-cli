# ruff: noqa: E402
import sys
import os
import unittest
import tempfile
import shutil
import tiktoken

# Add local mcp/ directory to sys.path so we can import search directly
_mcp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp")
if _mcp_dir not in sys.path:
    sys.path.insert(0, _mcp_dir)

from search import (
    SymbolMap,
    should_register,
    extract_identifiers,
    GitIgnoreFilter,
    is_binary_ext,
    is_generated_file,
    is_secret_like,
    handle_search
)


class TestSymbolMap(unittest.TestCase):
    def test_registration_and_apply(self):
        sym_map = SymbolMap()
        # Short strings should be rejected from mapping
        self.assertIsNone(sym_map.register("foo"))
        
        # Valid longer identifiers
        sig1 = sym_map.register("validateTokenSignature")
        sig2 = sym_map.register("processUserRequest")
        
        self.assertIsNotNone(sig1)
        self.assertIsNotNone(sig2)
        self.assertNotEqual(sig1, sig2)
        
        # Duplicate registration should return existing
        self.assertEqual(sym_map.register("validateTokenSignature"), sig1)
        
        # Test applying substitutions
        test_text = "def validateTokenSignature(req):\n    processUserRequest(req)"
        replaced = sym_map.apply(test_text)
        self.assertIn("α1", replaced)
        self.assertIn("α2", replaced)
        self.assertNotIn("validateTokenSignature", replaced)
        self.assertNotIn("processUserRequest", replaced)
        
        # Table output formatting
        table = sym_map.format_table()
        self.assertIn("§MAP:", table)
        self.assertIn("α1=validateTokenSignature", table)
        self.assertIn("α2=processUserRequest", table)

    def test_apply_descending_length_safety(self):
        sym_map = SymbolMap()
        # "validate" is a prefix of "validateToken"
        sym_map.register("validate")
        sym_map.register("validateToken")
        
        text = "we validate a validateToken here"
        replaced = sym_map.apply(text)
        
        # If "validate" replaced first, "validateToken" would become "α1Token", which is incorrect.
        # It must replace "validateToken" first, yielding "α2" and "validate" to "α1".
        self.assertNotIn("Token", replaced)


class TestROICompression(unittest.TestCase):
    def setUp(self):
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoder = tiktoken.encoding_for_model("gpt-4")

    def test_should_register(self):
        # Short string
        self.assertFalse(should_register("foo", 100, 1, self.encoder))
        
        # Extremely long identifier occurring many times (highly positive ROI)
        self.assertTrue(should_register("authenticate_user_credentials_handler", 10, 1, self.encoder))
        
        # Long identifier occurring only once (negative ROI due to lookup table overhead)
        self.assertFalse(should_register("authenticate_user_credentials_handler", 1, 1, self.encoder))

    def test_extract_identifiers(self):
        content = "authenticate_user_credentials_handler authenticate_user_credentials_handler " * 5
        content += " short word " * 2
        idents = extract_identifiers(content, "py", self.encoder)
        
        self.assertIn("authenticate_user_credentials_handler", idents)
        self.assertNotIn("short", idents)
        self.assertNotIn("word", idents)


class TestGitIgnoreFilter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.gi_filter = GitIgnoreFilter(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_gitignore_matching(self):
        # Write temporary .gitignore in root
        with open(os.path.join(self.temp_dir, ".gitignore"), "w") as f:
            f.write("# comment\n*.log\nbuild/\n")
            
        # Write sub-directory gitignore
        subdir = os.path.join(self.temp_dir, "src")
        os.makedirs(subdir, exist_ok=True)
        with open(os.path.join(subdir, ".gitignore"), "w") as f:
            f.write("target/\n")

        # Test root rules
        self.assertTrue(self.gi_filter.is_ignored(os.path.join(self.temp_dir, "error.log")))
        self.assertTrue(self.gi_filter.is_ignored(os.path.join(self.temp_dir, "build", "main.o")))
        self.assertFalse(self.gi_filter.is_ignored(os.path.join(self.temp_dir, "src", "main.py")))
        
        # Test recursive sub-directory rules
        self.assertTrue(self.gi_filter.is_ignored(os.path.join(subdir, "target", "debug")))
        self.assertFalse(self.gi_filter.is_ignored(os.path.join(self.temp_dir, "target", "debug")))


class TestCodeSearcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Patch workspace root in os.environ for db.get_workspace_root()
        os.environ["BUDDHI_WORKSPACE_ROOT"] = self.temp_dir

        # Create mock directories
        os.makedirs(os.path.join(self.temp_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "tests"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, ".git"), exist_ok=True)  # should be skipped

        # Create test code files
        self.file1 = os.path.join(self.temp_dir, "src", "app.py")
        self.file2 = os.path.join(self.temp_dir, "src", "utils.py")
        self.file3 = os.path.join(self.temp_dir, ".git", "config")
        self.file_large = os.path.join(self.temp_dir, "src", "large.py")
        self.file_binary = os.path.join(self.temp_dir, "src", "image.png")
        self.file_generated = os.path.join(self.temp_dir, "src", "app.min.js")
        self.file_secret = os.path.join(self.temp_dir, "src", "key.pem")

        # Code inside files
        with open(self.file1, "w", encoding="utf-8") as f:
            f.write("def setup_user_session():\n    print('setting up')\n    return 'success'\n")
        with open(self.file2, "w", encoding="utf-8") as f:
            f.write("def helper_session():\n    setup_user_session()\n    return True\n")
        with open(self.file3, "w", encoding="utf-8") as f:
            f.write("def setup_user_session():\n    pass\n")
        with open(self.file_large, "w", encoding="utf-8") as f:
            f.write("pass\n" * 100000)  # > 512KB
        with open(self.file_binary, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        with open(self.file_generated, "w", encoding="utf-8") as f:
            f.write("def setup_user_session(): pass")
        with open(self.file_secret, "w", encoding="utf-8") as f:
            f.write("def setup_user_session():\n    private_key = 'some_sensitive_stuff'\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        if "BUDDHI_WORKSPACE_ROOT" in os.environ:
            del os.environ["BUDDHI_WORKSPACE_ROOT"]

    def test_handle_search_basic(self):
        res = handle_search("setup_user_session", search_path=self.temp_dir)
        
        # Matches in app.py and utils.py
        self.assertIn("src/app.py:", res)
        self.assertIn("src/utils.py:", res)
        
        # Should not match in .git directory
        self.assertNotIn(".git/config", res)
        # Should skip large, binary, generated, and secret-like files
        self.assertNotIn("large.py", res)
        self.assertNotIn("image.png", res)
        self.assertNotIn("app.min.js", res)
        self.assertNotIn("key.pem", res)

    def test_handle_search_extension_filtering(self):
        res = handle_search("setup_user_session", search_path=self.temp_dir, ext_filter="py")
        self.assertIn("src/app.py:", res)
        
        res_js = handle_search("setup_user_session", search_path=self.temp_dir, ext_filter="js")
        self.assertNotIn("src/app.py:", res_js)

    def test_handle_search_secrets_filtering(self):
        secret_content_file = os.path.join(self.temp_dir, "src", "secrets.py")
        with open(secret_content_file, "w", encoding="utf-8") as f:
            f.write("# DB Config\nDB_API_KEY = \"abcd-efgh-ijkl-mnop-1234\"\n")
            
        res = handle_search("DB_API_KEY", search_path=self.temp_dir)
        # Should skip due to secret content matcher
        self.assertNotIn("secrets.py", res)

    def test_handle_search_stable_alphabetical_ordering(self):
        res = handle_search("setup_user_session", search_path=self.temp_dir)
        # app.py matches should appear before utils.py matches alphabetically
        idx_app = res.index("src/app.py:")
        idx_utils = res.index("src/utils.py:")
        self.assertTrue(idx_app < idx_utils)

    def test_pattern_limits_and_invalid_regex(self):
        # Invalid regex
        res_invalid = handle_search("(invalid", search_path=self.temp_dir)
        self.assertTrue(res_invalid.startswith("ERROR: invalid regex"))

        # Too long pattern
        res_long = handle_search("a" * 2000, search_path=self.temp_dir)
        self.assertTrue(res_long.startswith("ERROR: pattern too long"))


if __name__ == "__main__":
    unittest.main()
