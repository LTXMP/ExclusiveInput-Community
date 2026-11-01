# Exclusive XIM community configs

Free configs shared by Exclusive XIM users, with maintainer review before publication.

## Browse and copy

Open **Community** in the current desktop app. It loads this library automatically. Select a config, then choose Full config, Smart actions, Aim only or Calibration only. Browsing needs no GitHub account.

## Share a config

1. Save the config locally in Exclusive XIM.
2. Open **Community → Share config**, select it, add your contributor name and description, and confirm permission to share it under CC0.
3. Choose **Continue to submission**. The app prepares the complete JSON file and opens the submission form. Use **Show file** to locate it.
4. Attach that JSON file in the form and submit with your GitHub account.

The bot validates the package and creates a review. A maintainer checks the config, its description and image rights, then merges it. The app's browse index updates after merge. Invalid submissions receive a correction message. There are no paid packages or checkout links.

Preparing a file is not publication. The saved config includes its cover, connection settings, device selection, aim, calibration, mappings and macros; inspect it before sharing. The desktop app stores no GitHub token.

## Maintenance

`tools/submit_config.py` processes only labeled config submissions. It accepts one bounded JSON attachment from GitHub's file storage or one JSON code block. Payloads remain data and are never executed. Submission branches are tied to the issue number, and closed reviews cannot be silently reopened by editing old submissions.

`tools/build_index.py` validates free config packages and regenerates `index.json` after reviewed changes merge. The native client separately performs full runtime validation before import. Neither validation proves calibration accuracy or gameplay quality.

Run `python -m unittest discover -s tools -p 'test_*.py'` to check indexing and submission boundaries. The Review config submission workflow also exposes a manual test run. The automation uses the repository-scoped GitHub Actions token with job-specific permissions. No external server or shared desktop credential is required.
