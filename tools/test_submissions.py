import json
import unittest
from submit_config import attachment_url, trusted_download, read_package, MAX_BYTES


def sample():
    return dict(schema=1, license='CC0-1.0', author='Setup test', description='',
                config=dict(schema=1, name='Setup test', game='Custom game', aim={}, graph={}, bindings=[], output='Simulator'))


class Submissions(unittest.TestCase):
    def test_inline_package_and_exact_metadata(self):
        package = sample()
        self.assertEqual(read_package('```json\n' + json.dumps(package) + '\n```'), package)

    def test_attachment_package(self):
        url = 'https://github.com/user-attachments/files/123/config.json'
        seen = []
        def fetch(value):
            seen.append(value)
            return json.dumps(sample()).encode()
        self.assertEqual(read_package(f'[config.json]({url})', fetch), sample())
        self.assertEqual(seen, [url])

    def test_reject_ambiguous_or_missing_payloads(self):
        url = 'https://github.com/user-attachments/files/123/config.json'
        for body in ('', url + '\n' + url, url + '\n```json\n{}\n```'):
            with self.assertRaises(ValueError):
                read_package(body)

    def test_attachment_destination_boundaries(self):
        for url in ('http://github.com/user-attachments/files/1/a.json',
                    'https://github.com.evil.test/user-attachments/files/1/a.json',
                    'https://github.com/user-attachments/files/1/a.exe',
                    'https://github.com/user-attachments/files/1/a.json?url=http://localhost',
                    'https://github.com/user-attachments/files/1/../a.json'):
            self.assertFalse(attachment_url(url))
        for url in ('http://localhost/config.json', 'https://objects.githubusercontent.com.evil.test/x',
                    'https://user:pass@objects.githubusercontent.com/x', 'https://objects.githubusercontent.com:444/x'):
            self.assertFalse(trusted_download(url))

    def test_size_and_invalid_json(self):
        url = 'https://github.com/user-attachments/files/123/config.json'
        for data in (b'{' , b'x' * (MAX_BYTES + 1)):
            with self.assertRaises(ValueError):
                read_package(url, lambda _: data)

    def test_paid_or_invalid_packages_are_rejected(self):
        for key, value in (('license', 'Paid'), ('author', ''), ('price', 10)):
            package = sample(); package[key] = value
            with self.assertRaises(ValueError):
                read_package('```json\n' + json.dumps(package) + '\n```')


if __name__ == '__main__':
    unittest.main()
