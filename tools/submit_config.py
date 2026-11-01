"""Turn a validated config submission into a maintainer-reviewed pull request."""
import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from config_packages import validate_config

MAX_BYTES = 4 * 1024 * 1024
MARKER = '<!-- exclusivexim-submission -->'


def attachment_url(url):
    parts = urllib.parse.urlsplit(url)
    return (parts.scheme == 'https' and parts.netloc == 'github.com'
            and re.fullmatch(r'/user-attachments/files/[0-9]+/[A-Za-z0-9_.%~-]+\.json', parts.path)
            and not parts.query and not parts.fragment)


def trusted_download(url):
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ''
    return (parts.scheme == 'https' and not parts.username and not parts.password
            and parts.port in (None, 443)
            and (attachment_url(url) or host == 'objects.githubusercontent.com'
                 or re.fullmatch(r'github-production-user-asset-[a-z0-9-]+\.s3\.amazonaws\.com', host)))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download(url):
    opener = urllib.request.build_opener(NoRedirect)
    for _ in range(4):
        if not trusted_download(url):
            raise ValueError('The attachment redirected outside GitHub file storage.')
        try:
            with opener.open(urllib.request.Request(url, headers={'User-Agent': 'ExclusiveInput-Community'}), timeout=20) as response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError('Config exceeds 4 MiB.')
                return data
        except urllib.error.HTTPError as error:
            if error.code not in (301, 302, 303, 307, 308):
                raise ValueError('Could not download the attached file. Attach it again and edit the submission.') from None
            url = urllib.parse.urljoin(url, error.headers.get('Location', ''))
    raise ValueError('The attachment redirected too many times.')


def read_package(body, fetch=download):
    if len(body.encode()) > 65536:
        raise ValueError('Submission text exceeds limits.')
    urls = re.findall(r'https://github\.com/user-attachments/files/[^\s)<>]+', body)
    blocks = re.findall(r'```json\s*\n(.*?)\n```', body, re.S)
    if len(urls) + len(blocks) != 1:
        raise ValueError('Attach exactly one .json config file prepared by ExclusiveInput.')
    if urls:
        if not attachment_url(urls[0]):
            raise ValueError('Attach a .json file using the GitHub attachment button.')
        data = fetch(urls[0])
    else:
        data = blocks[0].encode()
    if len(data) > MAX_BYTES:
        raise ValueError('Config exceeds 4 MiB.')
    try:
        package = json.loads(data)
    except (ValueError, UnicodeError):
        raise ValueError('The attached file is not valid JSON.') from None
    return validate_config(package)


class GitHub:
    def __init__(self, repository, token):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Invalid repository.')
        self.repository, self.token = repository, token

    def request(self, method, path, body=None):
        request = urllib.request.Request('https://api.github.com' + path,
            data=None if body is None else json.dumps(body).encode(), method=method,
            headers={'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                     'Content-Type': 'application/json', 'User-Agent': 'ExclusiveInput-Community'})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response) if response.status != 204 else None

    def repo(self, method, path, body=None):
        return self.request(method, '/repos/' + self.repository + path, body)


def review_submission(api, issue, package):
    number = int(issue['number'])
    branch = f'submission-{number}'
    name = f'community-{number}.json'
    repository = api.repo('GET', '')
    default = repository['default_branch']
    pulls = api.repo('GET', '/pulls?state=all&head=' + urllib.parse.quote(api.repository.split('/')[0] + ':' + branch))
    if pulls and pulls[0]['state'] == 'closed':
        raise ValueError('This submission has already been reviewed. Open a new submission for an update.')
    try:
        api.repo('GET', '/git/ref/heads/' + branch)
        if not pulls or pulls[0]['user']['login'] != 'github-actions[bot]':
            raise ValueError('The review branch is already in use. Contact the maintainer.')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        head = api.repo('GET', '/git/ref/heads/' + default)['object']['sha']
        api.repo('POST', '/git/refs', {'ref': 'refs/heads/' + branch, 'sha': head})
    path = '/contents/configs/' + name
    sha = None
    try:
        sha = api.repo('GET', path + '?ref=' + branch)['sha']
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    content = (json.dumps(package, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    body = {'message': f'Add config from submission #{number}', 'branch': branch,
            'content': base64.b64encode(content).decode()}
    if sha:
        body['sha'] = sha
    api.repo('PUT', path, body)
    title = '[Config] ' + package['config']['name'][:100]
    description = (f'Validated free CC0 config from #{number}.\n\n'
                   'Review the config and image rights before merging. Validation checks format and bounds; '
                   'it does not establish calibration accuracy or gameplay quality. '
                   'The browse index updates automatically after merge.\n\n'
                   f'Closes #{number}')
    if pulls:
        result = api.repo('PATCH', '/pulls/' + str(pulls[0]['number']), {'title': title, 'body': description})
    else:
        result = api.repo('POST', '/pulls', {'title': title, 'body': description, 'head': branch, 'base': default})
    return result['html_url']


def main():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    issue = event['issue']
    api = GitHub(os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN'])
    # Pull requests also expose an issue object; only accept actual open submissions.
    if 'pull_request' in issue or issue['state'] != 'open' or not any(label['name'] == 'config-submission' for label in issue['labels']):
        return
    try:
        package = read_package(issue.get('body') or '')
        url = review_submission(api, issue, package)
        message = f'{MARKER}\nConfig validated and ready for [maintainer review]({url}). It will appear in the app after approval and merge.'
    except ValueError as error:
        message = f'{MARKER}\nSubmission needs attention: {error}'
    comments = api.repo('GET', f'/issues/{issue["number"]}/comments?per_page=100')
    previous = next((c for c in comments if c['user']['login'] == 'github-actions[bot]' and c['body'].startswith(MARKER)), None)
    if previous:
        api.repo('PATCH', '/issues/comments/' + str(previous['id']), {'body': message})
    else:
        api.repo('POST', f'/issues/{issue["number"]}/comments', {'body': message})


if __name__ == '__main__':
    main()
