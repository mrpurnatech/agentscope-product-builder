import boto3
from github import Github
from config.settings import AWS_REGION, GITHUB_SECRET_NAME


def get_token() -> str:
    client = boto3.client(
        service_name="secretsmanager",
        region_name=AWS_REGION
    )
    return client.get_secret_value(
        SecretId=GITHUB_SECRET_NAME
    )["SecretString"]


def run(plan: dict, files: dict) -> str:
    print(f"\n[GitHubAgent] Pushing {len(files)} files...")

    g = Github(get_token())
    user = g.get_user()

    repo = user.create_repo(
        name=plan["repo_name"],
        description=plan["description"],
        private=plan["private"],
        auto_init=False
    )
    print(f"  Repo: {repo.html_url}")

    success = 0
    for path, content in files.items():
        try:
            repo.create_file(
                path=path,
                message=f"feat: add {path}",
                content=content or ""
            )
            success += 1
        except Exception as e:
            print(f"  Skipped {path}: {e}")

    print(f"  Pushed {success}/{len(files)} files ✅")
    return repo.html_url