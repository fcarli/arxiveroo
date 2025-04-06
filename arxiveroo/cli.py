#!/usr/bin/env python3
import os
import subprocess
import sys

import click


@click.group()
def cli():
    """Command line interface for arxiveroo."""


@cli.command()
@click.option("--port", "-p", default=8000, help="Port to run the Chainlit server on")
def run(port):
    """Run the Chainlit chatbot server."""
    # Get the directory of the chatbot.py file
    chatbot_dir = os.path.join(os.path.dirname(__file__), "chatbot")
    chatbot_path = os.path.join(chatbot_dir, "chatbot.py")

    # Check if the file exists
    if not os.path.exists(chatbot_path):
        click.echo(f"Error: Could not find {chatbot_path}")
        sys.exit(1)

    # Change to the chatbot directory and run the command
    original_dir = os.getcwd()
    os.chdir(os.path.dirname(chatbot_path))

    # Run the Chainlit command
    try:
        click.echo(f"Starting Chainlit server on port {port}...")
        subprocess.run(["chainlit", "run", "chatbot.py", "-w", "--port", str(port)], check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running Chainlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("Server stopped.")
    finally:
        os.chdir(original_dir)


if __name__ == "__main__":
    cli()
