

class TestStructuredErrors:
    def test_http_request_error_has_error_type(self):
        from unittest.mock import patch, MagicMock
        from urllib.error import URLError
        plugin = OpenClawPlugin()
        with patch('plugins.openclaw.backend.urlopen', side_effect=URLError('connection refused')):
            result = plugin.http_request(None, {'method': 'GET', 'url': 'http://fake'})
        assert 'error_type' in result
        assert result['error_type'] == 'network_error'

    def test_exec_timeout_has_error_type(self):
        import subprocess
        from unittest.mock import patch
        plugin = OpenClawPlugin()
        with patch('plugins.openclaw.backend.subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 1)):
            result = plugin.exec_command(None, {'command': 'sleep 99'})
        assert result.get('error_type') == 'timeout'

    def test_knowflow_record_warning_on_update_failure(self):
        from unittest.mock import patch, MagicMock
        from urllib.error import HTTPError
        plugin = OpenClawPlugin()

        create_response = MagicMock()
        create_response.__enter__ = lambda s: s
        create_response.__exit__ = MagicMock(return_value=False)
        create_response.read.return_value = b'{"id": "test-id-123"}'

        def mock_urlopen(req, timeout=30):
            if 'openclaw' in req.full_url:
                raise HTTPError(req.full_url, 404, 'Not Found', {}, None)
            return create_response

        with patch('plugins.openclaw.backend.urlopen', side_effect=mock_urlopen):
            result = plugin.knowflow_record(None, {
                'name': 'test', 'project_id': 'proj1'
            })
        assert result['success'] is True
        assert 'warning' in result
