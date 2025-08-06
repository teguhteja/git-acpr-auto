# AI-Powered Git Assistant (git-acpr-automatic)

A command-line tool that automates the Git workflow (`add`, `commit`, `push`, and `pull request`) using Google's Gemini AI to intelligently generate commit messages and pull request descriptions.

## Features

-   **Automated Staging:** Automatically stages all modified files (`git add .`).
-   **AI-Generated Commit Messages:** Analyzes staged changes (`git diff`) and generates concise, descriptive commit messages in the conventional commit format.
-   **AI-Generated Pull Requests:** Fills out a PR template with a detailed description, summary of changes, and more, based on the code diff.
-   **Flexible Workflow:** Choose which steps to run (`add`, `commit`, `push`, `pr`) using the `--steps` flag.
-   **Handles Existing Commits:** Can push and create a PR for local commits that haven't been pushed yet.
-   **Highly Configurable:** Customize behavior using a configuration file (`.conf`) and command-line arguments.
-   **Safety Checks:** Includes safeguards like a repository size check and warnings when operating on the main/develop branch.

## Prerequisites

-   Python 3.7+
-   Git
-   GitHub CLI (`gh`)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd git_acpr_automatic
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install and Authenticate GitHub CLI:**
    Follow the installation instructions at cli.github.com. Then, authenticate with your GitHub account:
    ```bash
    gh auth login
    ```

4.  **Set up your API Key:**
    This project uses the Google Gemini API.
    -   Get your API key from Google AI Studio.
    -   Create a file named `.env` in the root of the project directory.
    -   Add your API key to the `.env` file:
        ```
        GANAI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
        ```

5.  **(Optional) Create a Configuration File:**
    You can customize default settings. Create a directory `conf` and a file `git_acp.conf` inside it.
    ```bash
    mkdir conf
    touch conf/git_acp.conf
    ```
    Here is an example configuration:
    ```ini
    # conf/git_acp.conf
    [settings]
    model = gemini-1.5-pro-latest
    max-kb = 200
    branch-pr = main
    pr-template = prompt/pull_request_template.md
    ```

## Usage

The main script is `main.py`. You can run it from the root of the project directory. The tool will guide you with prompts for confirmation.

### Basic Commands

-   **Full Workflow (Add, Commit, Push, Pull Request):**
    ```bash
    python main.py
    # or explicitly
    python main.py --steps acpr
    ```

-   **Add and Commit Only:**
    ```bash
    python main.py --steps ac
    ```

-   **Push existing commits and create a PR:**
    If you have local commits that are not pushed, you can run the push and PR steps.
    ```bash
    python main.py --steps pr
    ```
    *(The script will detect unpushed commits and use them to generate the PR).*

### Command-Line Arguments

Command-line arguments override settings from the configuration file.

| Argument          | Short | Description                                                        | Default                           |
| ----------------- | ----- | ------------------------------------------------------------------ | --------------------------------- |
| `--steps`         |       | Steps to run: a(add), c(commit), p(push), pr(pull request).         | `acpr`                            |
| `--target-branch` |       | The target branch for the pull request.                            | `develop`                         |
| `--model`         | `-m`  | The Gemini model to use for generation.                            | `gemini-1.5-flash-latest`         |
| `--max-kb`        | `-k`  | Max repository size (in KB) to run. A safety check.                | `100`                             |
| `--pr-template`   |       | Path to the pull request template file.                            | `prompt/pull_request_template.md` |
| `--config`        | `-c`  | Path to the configuration file.                                    | `conf/git_acp.conf`               |

### Example

```bash
# Make some code changes...

# Run the full workflow, targeting the 'main' branch
python main.py --steps acpr --target-branch main

# The script will:
# 1. Add all changes to staging.
# 2. Generate a commit message and ask for confirmation.
# 3. Commit the changes.
# 4. Push the current branch to origin.
# 5. Generate a PR title and body and ask for confirmation.
# 6. Create the pull request on GitHub.
```
