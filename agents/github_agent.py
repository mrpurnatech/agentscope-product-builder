"""GitHub Agent — repo creation + file push via AWS Secrets Manager."""
import boto3
from github import Github
from agentscope.message import Msg
from agents.base import ProductAgent
from config.settings import AWS_REGION, GITHUB_SECRET_NAME


def get_token() -> str:
    """Fetch GitHub PAT from AWS Secrets Manager."""
    client = boto3.client(
        service_name="secretsmanager",
        region_name=AWS_REGION,
    )
    return client.get_secret_value(SecretId=GITHUB_SECRET_NAME)["SecretString"]


class GitHubAgent(ProductAgent):
    """Creates GitHub repo and pushes all generated files."""

    def __init__(self) -> None:
        # No model — this agent uses GitHub API, not LLM
        super().__init__(
            name="github",
            model=None,
            sys_prompt="",
        )

    async def push(self, plan_meta: dict, files: dict) -> str:
        """Create repo and push all files. Returns repo URL."""
        print(f"\n[github] Pushing {len(files)} files...")

        g = Github(get_token())
        user = g.get_user()

        repo = user.create_repo(
            name=plan_meta.get("repo_name", "agentscope-project"),
            description=plan_meta.get("description", ""),
            private=plan_meta.get("private", False),
            auto_init=False,
        )
        print(f"  Repo: {repo.html_url}")

        success = 0
        for path, content in files.items():
            try:
                repo.create_file(
                    path=path,
                    message=f"feat: add {path}",
                    content=content or "",
                )
                success += 1
            except Exception as e:
                print(f"  Skipped {path}: {e}")

        print(f"  Pushed {success}/{len(files)} files")
        return repo.html_url

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        all_files = ctx.get("all_files", {})
        architecture = ctx.get("architecture", {})
        parsed_prd = ctx.get("parsed_prd", {})

        plan_meta = {
            "repo_name": architecture.get("repo_name", parsed_prd.get("product_name", "project")),
            "description": architecture.get("description", ""),
            "private": False,
        }

        url = await self.push(plan_meta, all_files)
        ctx["repo_url"] = url
        return self.make_reply(f"Pushed to {url}", ctx)
