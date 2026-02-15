import os
import subprocess

import click


@click.command()
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish"]),
    default=None,
    help="Shell type (auto-detected from $SHELL if omitted).",
)
def completion(shell):
    """Output shell completion script for awiz."""
    if shell is None:
        login_shell = os.path.basename(os.environ.get("SHELL", ""))
        if login_shell in ("bash", "zsh", "fish"):
            shell = login_shell
        else:
            raise click.UsageError(
                "Could not detect shell. Pass --shell bash|zsh|fish explicitly."
            )

    env_val = f"{shell}_source"
    result = subprocess.run(
        ["awiz"],
        env={**os.environ, "_AWIZ_COMPLETE": env_val},
        capture_output=True,
        text=True,
    )
    output = result.stdout
    # macOS ships bash 3.2 which doesn't support the -o nosort flag
    if shell == "bash":
        output = output.replace("-o nosort", "")
    click.echo(output)

    # Print setup hint to stderr so it doesn't pollute piped output
    hints = {
        "bash": 'eval "$(awiz completion --shell bash)"  # or append to ~/.bashrc',
        "zsh": 'eval "$(awiz completion --shell zsh)"  # or append to ~/.zshrc',
        "fish": "awiz completion --shell fish | source  # or save to ~/.config/fish/completions/awiz.fish",
    }
    click.echo(f"\n# Activate with:\n#   {hints[shell]}", err=True)
