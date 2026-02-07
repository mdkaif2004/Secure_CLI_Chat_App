import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

from core.session_manager import SessionManager
from utils.validators import validate_connection_code

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
    "chat_peer": "green",
    "chat_self": "cyan",
    "encrypted": "dim white"
})

console = Console(theme=custom_theme)

class SecureChatCLI:
    def __init__(self):
        self.session_manager = SessionManager(self.ui_callback)
        self.session = PromptSession()
        self.running = True

    def ui_callback(self, event_type, data=None):
        # This is called from the asyncio loop when state changes or messages arrive
        if event_type == "SEARCHING":
            console.print("[info]Searching for peer... (Timeout: 60s)[/info]")
        elif event_type == "USER_FOUND":
            console.print("[success]Peer found! Initiating Handshake...[/success]")
        elif event_type == "KEY_SETUP":
            console.print("[info]Generating Ephemeral Keys & Exchanging...[/info]")
        elif event_type == "CONNECTED":
            console.print(Panel("[bold green]SECURE ENCRYPTED CHANNEL ESTABLISHED[/bold green]\n[dim]All messages are E2E encrypted. Session is ephemeral.[/dim]", expand=False))
        elif event_type == "MESSAGE":
            # Peer message
            console.print(f"[chat_peer]Peer:[/chat_peer] {data}")
        elif event_type == "DISCONNECTED":
            console.print("[danger]Peer Disconnected.[/danger]")
            self.running = False
        elif event_type == "DESTROYED":
            console.print("[danger]Session Destroyed. Exiting...[/danger]")
            self.running = False
        elif event_type == "ERROR":
             console.print(f"[danger]Error: {data}[/danger]")

    async def run(self):
        console.clear()
        console.print(Panel.fit("[bold white]SECURE CLI CHAT[/bold white]\n[dim]Zero Trace. Zero Trust.[/dim]", style="blue"))

        # 1. Get Room Code
        while True:
            room_code = await self.session.prompt_async("Enter Room Code (8-16 chars): ")
            room_code = room_code.strip()
            if validate_connection_code(room_code):
                break
            console.print("[warning]Invalid format. Use A-Z, 0-9, length 8-16.[/warning]")

        # 2. Start Session
        try:
            await self.session_manager.start_session(room_code)
        except Exception as e:
            console.print(f"[danger]Failed to start: {e}[/danger]")
            return

        # 3. Chat Loop
        with patch_stdout():
            while self.running:
                try:
                    # We use a timeout so we can check self.running periodically if prompt blocks
                    # But prompt_async is awaitable, so we can just wait.
                    # However, we need to be able to exit if the peer disconnects while we are typing.
                    # We can use asyncio.wait with a task for the input.
                    
                    input_task = asyncio.create_task(self.session.prompt_async("You: "))
                    done, pending = await asyncio.wait([input_task], return_when=asyncio.FIRST_COMPLETED)
                    
                    if input_task in done:
                        text = input_task.result().strip()
                        if text:
                             if text.lower() == "/quit":
                                 await self.session_manager.destroy_session()
                                 break
                             # Optimistic UI update
                             console.print(f"[chat_self]You:[/chat_self] {text}")
                             await self.session_manager.send_message(text)
                    else:
                        # If we woke up but input isn't done, it might be because self.running changed
                        # Cancellation would be needed here in a more robust app
                        input_task.cancel()
                        
                    if not self.running:
                        break

                except (EOFError, KeyboardInterrupt):
                    await self.session_manager.destroy_session()
                    break
