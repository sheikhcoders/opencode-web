"""CLI module for OpenCode Web."""
import asyncio
import click
import websockets
from opencode_web.server.main import run_server

@click.group()
def main():
    """Main entry point for the opencode CLI."""

@main.command()
@click.option('--port', default=None, type=int, help='Port to run the server on.')
@click.option('--hostname', default='127.0.0.1', help='Hostname to bind to.')
@click.option('--mdns', is_flag=True, help='Enable mDNS discovery.')
@click.option('--mdns-domain', default='opencode.local', help='mDNS domain name.')
@click.option('--cors', multiple=True, help='CORS allowed domains.')
def web(port, hostname, mdns, mdns_domain, cors):
    """Start the web interface."""
    run_server(port=port, hostname=hostname, mdns=mdns, mdns_domain=mdns_domain, cors=cors)

async def attach_terminal(url):
    """Asynchronous function to attach to the terminal WebSocket."""
    # Determine the websocket URL
    ws_url = url.rstrip('/').replace("http://", "ws://").replace("https://", "wss://") + "/ws/terminal"

    try:
        async with websockets.connect(ws_url) as websocket:
            click.echo(f"Connected to {ws_url}")

            # Initial message from server
            welcome = await websocket.recv()
            click.echo(welcome)

            while True:
                line = input("> ")
                if not line:
                    continue
                await websocket.send(line)
                if line.strip().lower() == 'exit':
                    break
                response = await websocket.recv()
                click.echo(response)
    except Exception as e: # pylint: disable=broad-exception-caught
        click.echo(f"Error attaching to server: {e}")

@main.command()
@click.argument('url')
def attach(url):
    """Attach a terminal TUI to a running web server."""
    click.echo(f"Attaching to {url}...")
    asyncio.run(attach_terminal(url))

if __name__ == '__main__':
    main()
