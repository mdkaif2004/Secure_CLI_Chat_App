import asyncio
from ui.cli import SecureChatCLI

def main():
    cli = SecureChatCLI()
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    main()
