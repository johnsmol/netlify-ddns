from unittest.mock import MagicMock, patch

import pytest

import main

SAMPLE_RECORDS = [
    {'id': 'rec-a', 'hostname': 'home.example.com', 'type': 'A', 'value': '1.2.3.4'},
    {'id': 'rec-aaaa', 'hostname': 'home.example.com', 'type': 'AAAA', 'value': '2001:db8::1'},
    {'id': 'rec-other', 'hostname': 'other.example.com', 'type': 'A', 'value': '5.6.7.8'},
]


@pytest.fixture(autouse=True)
def configure_globals():
    """Set module globals to known values before each test."""
    main.FQDN = 'home.example.com'
    main.API_TOKEN = 'test-token'
    main.ZONE_SLUG = 'example_com'
    main.headers = {
        'Content-Type': 'application/json;charset=utf-8',
        'Authorization': 'Bearer test-token',
    }
    yield


class TestSetup:
    def test_valid_config_sets_globals(self, monkeypatch):
        monkeypatch.setenv('FQDN', 'home.example.com')
        monkeypatch.setenv('NETLIFY_API_TOKEN', 'tok')
        with patch('main.load_dotenv'):
            main.setup()
        assert main.FQDN == 'home.example.com'
        assert main.API_TOKEN == 'tok'
        assert main.ZONE_SLUG == 'example_com'
        assert main.headers['Authorization'] == 'Bearer tok'

    def test_missing_fqdn_exits(self, monkeypatch):
        monkeypatch.delenv('FQDN', raising=False)
        monkeypatch.setenv('NETLIFY_API_TOKEN', 'tok')
        with patch('main.load_dotenv'):
            with pytest.raises(SystemExit):
                main.setup()

    def test_missing_token_exits(self, monkeypatch):
        monkeypatch.setenv('FQDN', 'home.example.com')
        monkeypatch.delenv('NETLIFY_API_TOKEN', raising=False)
        with patch('main.load_dotenv'):
            with pytest.raises(SystemExit):
                main.setup()

    def test_invalid_fqdn_exits(self, monkeypatch):
        monkeypatch.setenv('FQDN', 'not-a-valid-domain')
        monkeypatch.setenv('NETLIFY_API_TOKEN', 'tok')
        with patch('main.load_dotenv'):
            with pytest.raises(SystemExit):
                main.setup()


class TestGetPublicIpAddress:
    def _mock_response(self, ip):
        mock = MagicMock()
        mock.json.return_value = {'ip': ip}
        return mock

    def test_ipv4_success(self):
        with patch('requests.get', return_value=self._mock_response('1.2.3.4')):
            assert main.get_public_ip_address(version=4) == '1.2.3.4'

    def test_ipv6_success(self):
        with patch('requests.get', return_value=self._mock_response('2001:db8::1')):
            assert main.get_public_ip_address(version=6) == '2001:db8::1'

    def test_ipv4_failure_exits(self):
        with patch('requests.get', side_effect=Exception('timeout')):
            with pytest.raises(SystemExit):
                main.get_public_ip_address(version=4)

    def test_ipv6_failure_returns_none(self):
        with patch('requests.get', side_effect=Exception('timeout')):
            assert main.get_public_ip_address(version=6) is None

    def test_ipv4_uses_v4_endpoint(self):
        with patch('requests.get', return_value=self._mock_response('1.2.3.4')) as mock_get:
            main.get_public_ip_address(version=4)
        mock_get.assert_called_once_with(main.PUBLIC_IPV4_URI, timeout=15)

    def test_ipv6_uses_v6_endpoint(self):
        with patch('requests.get', return_value=self._mock_response('2001:db8::1')) as mock_get:
            main.get_public_ip_address(version=6)
        mock_get.assert_called_once_with(main.PUBLIC_IPV6_URI, timeout=15)


class TestGetDnsRecords:
    def test_success_returns_records(self):
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_RECORDS
        with patch('requests.get', return_value=mock_response):
            assert main.get_dns_records() == SAMPLE_RECORDS

    def test_failure_exits(self):
        with patch('requests.get', side_effect=Exception('timeout')):
            with pytest.raises(SystemExit):
                main.get_dns_records()


class TestExtractTargetRecordId:
    def test_a_record_found(self):
        record_id, record_ip = main.extract_target_record_id(SAMPLE_RECORDS, 'A')
        assert record_id == 'rec-a'
        assert record_ip == '1.2.3.4'

    def test_aaaa_record_found(self):
        record_id, record_ip = main.extract_target_record_id(SAMPLE_RECORDS, 'AAAA')
        assert record_id == 'rec-aaaa'
        assert record_ip == '2001:db8::1'

    def test_type_not_found_returns_none(self):
        record_id, record_ip = main.extract_target_record_id(SAMPLE_RECORDS, 'MX')
        assert record_id is None
        assert record_ip is None

    def test_different_hostname_not_matched(self):
        records = [{'id': 'rec1', 'hostname': 'other.example.com', 'type': 'A', 'value': '1.2.3.4'}]
        record_id, record_ip = main.extract_target_record_id(records, 'A')
        assert record_id is None
        assert record_ip is None

    def test_empty_records_returns_none(self):
        record_id, record_ip = main.extract_target_record_id([], 'A')
        assert record_id is None
        assert record_ip is None


class TestCreateDnsRecord:
    def test_success_returns_json(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'new-rec'}
        with patch('requests.post', return_value=mock_response):
            result = main.create_dns_record('home.example.com', '1.2.3.4', 'A')
        assert result == {'id': 'new-rec'}

    def test_non_201_exits(self):
        mock_response = MagicMock()
        mock_response.status_code = 422
        with patch('requests.post', return_value=mock_response):
            with pytest.raises(SystemExit):
                main.create_dns_record('home.example.com', '1.2.3.4', 'A')

    def test_request_exception_exits(self):
        with patch('requests.post', side_effect=Exception('timeout')):
            with pytest.raises(SystemExit):
                main.create_dns_record('home.example.com', '1.2.3.4', 'A')

    def test_record_type_sent_in_body(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {}
        with patch('requests.post', return_value=mock_response) as mock_post:
            main.create_dns_record('home.example.com', '2001:db8::1', 'AAAA')
        body = mock_post.call_args.kwargs['json']
        assert body['type'] == 'AAAA'


class TestDeleteDnsRecord:
    def test_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 204
        with patch('requests.delete', return_value=mock_response):
            main.delete_dns_record('rec-a')  # should not raise

    def test_non_204_exits(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch('requests.delete', return_value=mock_response):
            with pytest.raises(SystemExit):
                main.delete_dns_record('rec-a')

    def test_request_exception_exits(self):
        with patch('requests.delete', side_effect=Exception('timeout')):
            with pytest.raises(SystemExit):
                main.delete_dns_record('rec-a')


class TestUpdateRecord:
    def test_none_ip_skips_entirely(self):
        with patch('main.create_dns_record') as mock_create:
            with patch('main.delete_dns_record') as mock_delete:
                main.update_record(SAMPLE_RECORDS, None, 'AAAA')
        mock_create.assert_not_called()
        mock_delete.assert_not_called()

    def test_no_existing_record_creates_only(self):
        with patch('main.create_dns_record') as mock_create:
            with patch('main.delete_dns_record') as mock_delete:
                main.update_record([], '1.2.3.4', 'A')
        mock_create.assert_called_once_with('home.example.com', '1.2.3.4', 'A')
        mock_delete.assert_not_called()

    def test_ip_changed_creates_then_deletes(self):
        with patch('main.create_dns_record') as mock_create:
            with patch('main.delete_dns_record') as mock_delete:
                main.update_record(SAMPLE_RECORDS, '9.9.9.9', 'A')
        mock_create.assert_called_once_with('home.example.com', '9.9.9.9', 'A')
        mock_delete.assert_called_once_with('rec-a')

    def test_ip_unchanged_skips(self):
        with patch('main.create_dns_record') as mock_create:
            with patch('main.delete_dns_record') as mock_delete:
                main.update_record(SAMPLE_RECORDS, '1.2.3.4', 'A')
        mock_create.assert_not_called()
        mock_delete.assert_not_called()
