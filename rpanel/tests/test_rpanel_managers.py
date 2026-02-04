
import unittest
from unittest.mock import patch, MagicMock, mock_open
import frappe
from rpanel.hosting.nginx_manager import NginxManager
from rpanel.hosting.git_manager import clone_repository, pull_latest
from rpanel.hosting.database_manager import execute_query, get_tables

class TestNginxManager(unittest.TestCase):
    def setUp(self):
        self.manager = NginxManager()
        self.domain = "test.example.com"
        self.site_path = "/var/www/test.example.com"

    @patch('rpanel.hosting.nginx_manager.subprocess.run')
    @patch('rpanel.hosting.nginx_manager.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_create_website_config(self, mock_file, mock_exists, mock_run):
        """Test creating a new website configuration"""
        mock_exists.return_value = False # Config doesn't exist yet
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        self.manager.create_website_config(self.domain, self.site_path)

        # Verify subprocess calls (tee, chmod, ln, nginx -t, reload)
        self.assertTrue(mock_run.called)
        
        # Verify checking for protected configs
        self.assertFalse(self.manager.is_protected_config("rpanel-test_example_com.conf"))

    def test_is_protected_config(self):
        """Test protected configuration detection"""
        self.assertTrue(self.manager.is_protected_config("frappe-bench-frappe"))
        self.assertTrue(self.manager.is_protected_config("ollama-proxy.conf"))
        self.assertFalse(self.manager.is_protected_config("rpanel-random-site.conf"))

    @patch('rpanel.hosting.nginx_manager.subprocess.run')
    def test_enable_disable_site(self, mock_run):
        """Test enabling and disabling sites"""
        mock_run.return_value = MagicMock(returncode=0)
        config_name = "rpanel-test_site.conf"

        # Enable
        with patch('rpanel.hosting.nginx_manager.Path.exists') as mock_exists:
            mock_exists.return_value = False # Target symlink doesn't exist
            self.manager.enable_site(config_name)
            mock_run.assert_called() # Should call ln -s

        # Disable
        self.manager.disable_site(config_name)
        mock_run.assert_called() # Should call rm -f

    @patch('rpanel.hosting.nginx_manager.subprocess.run')
    def test_test_and_reload_success(self, mock_run):
        """Test successful Nginx reload"""
        # Mock nginx -t success
        mock_run.return_value = MagicMock(returncode=0, stdout="syntax is ok", stderr="")
        
        self.manager.test_and_reload()
        
        # Should call systemctl reload nginx
        found_reload = False
        for call in mock_run.call_args_list:
            args = call[0][0]
            if args == ['sudo', 'systemctl', 'reload', 'nginx']:
                found_reload = True
                break
        self.assertTrue(found_reload)


class TestGitManager(unittest.TestCase):
    def setUp(self):
        self.website_name = "test-site"
        self.repo_url = "https://github.com/example/repo.git"
        
        # Mock website doc
        self.mock_website = MagicMock()
        self.mock_website.site_path = "/var/www/test-site"
        self.mock_website.git_branch = "main"

    @patch('rpanel.hosting.git_manager.frappe.get_doc')
    @patch('rpanel.hosting.git_manager.subprocess.run')
    @patch('rpanel.hosting.git_manager.os.path.exists')
    @patch('rpanel.hosting.git_manager.os.makedirs')
    @patch('rpanel.hosting.git_manager.os.listdir')
    def test_clone_repository_success(self, mock_listdir, mock_makedirs, mock_exists, mock_run, mock_get_doc):
        mock_get_doc.return_value = self.mock_website
        mock_exists.return_value = False # Directory doesn't exist
        mock_run.return_value = MagicMock(returncode=0)
        
        result = clone_repository(self.website_name, self.repo_url)
        
        self.assertTrue(result['success'])
        mock_run.assert_called() # Should run git clone
        self.mock_website.db_set.assert_called() # Should save properties

    @patch('rpanel.hosting.git_manager.frappe.get_doc')
    @patch('rpanel.hosting.git_manager.subprocess.run')
    @patch('rpanel.hosting.git_manager.os.path.exists')
    def test_pull_latest_success(self, mock_exists, mock_run, mock_get_doc):
        mock_get_doc.return_value = self.mock_website
        mock_exists.return_value = True # .git exists
        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.")
        
        result = pull_latest(self.website_name)
        
        self.assertTrue(result['success'])
        mock_run.assert_called() # Should run git pull


class TestDatabaseManager(unittest.TestCase):
    @patch('rpanel.hosting.database_manager.subprocess.run')
    def test_execute_query_select(self, mock_run):
        """Test executing valid SELECT query"""
        mock_run.return_value = MagicMock(returncode=0, stdout='[{"id": 1, "name": "Test"}]')
        
        result = execute_query("test_db", "SELECT * FROM users")
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(result['data'][0]['name'], "Test")
    
    def test_execute_query_blocked(self):
        """Test blocking non-SELECT queries"""
        result = execute_query("test_db", "DROP TABLE users")
        self.assertFalse(result['success'])
        self.assertIn("Only SELECT", result['error'])

    @patch('rpanel.hosting.database_manager.subprocess.run')
    def test_get_tables(self, mock_run):
        """Test retrieving tables"""
        mock_run.return_value = MagicMock(returncode=0, stdout='["table1", "table2"]')
        
        result = get_tables("test_db")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['tables'], ["table1", "table2"])
