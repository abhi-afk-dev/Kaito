import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv # <--- This is the key!
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# 1. LOAD .ENV
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Verify we have the secrets
CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
USER_EMAIL = os.getenv("USER_GOOGLE_EMAIL")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ ERROR: Could not find GOOGLE_OAUTH_CLIENT_ID or SECRET in .env")
    print(f"   Looking in: {ENV_PATH}")
    sys.exit(1)

# 2. SETUP PATHS
CURRENT_PYTHON = Path(sys.executable)
BIN_DIR = CURRENT_PYTHON.parent
EXECUTABLE = BIN_DIR / "workspace-mcp"
if not EXECUTABLE.exists():
    EXECUTABLE = Path("/home/abhi/projects/Kaito_Web/env/bin/workspace-mcp")

CREDENTIALS_DIR = Path.home() / ".google_workspace_mcp" / "credentials"

async def run_auth():
    print(f"\n🚀 KAITO AUTH REPAIR KIT (ENV LOADED)")
    print(f"   Client ID: {CLIENT_ID[:10]}... (Loaded)")
    print(f"   Email: {USER_EMAIL}")
    
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)
    
    # 3. PREPARE ENVIRONMENT
    # We copy the current env (which now includes .env vars)
    mcp_env = os.environ.copy()
    mcp_env["CREDENTIALS_DIR"] = str(CREDENTIALS_DIR)
    # Explicitly ensure these are set for the subprocess
    mcp_env["GOOGLE_OAUTH_CLIENT_ID"] = CLIENT_ID
    mcp_env["GOOGLE_OAUTH_CLIENT_SECRET"] = CLIENT_SECRET
    mcp_env["USER_GOOGLE_EMAIL"] = USER_EMAIL
    mcp_env["MCP_SINGLE_USER_MODE"] = "true"
    
    server_params = StdioServerParameters(
        command=str(EXECUTABLE), 
        args=[],
        env=mcp_env
    )

    print("\n🔗 Connecting to Server...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("⚡ Poking the server with your credentials...")
                
                # 4. TRIGGER AUTH
                task = asyncio.create_task(
                    session.call_tool("search_gmail_messages", arguments={
                        "query": "welcome",
                        "user_google_email": USER_EMAIL 
                    })
                )
                
                print("\n" + "="*60)
                print("👀 LOOK DOWN! The URL should appear below.")
                print("============================================================")

                # Keep alive loop
                for i in range(120):
                    if len(os.listdir(CREDENTIALS_DIR)) > 0:
                         print("\n\n✅ SUCCESS! Token file detected!")
                         print("   You can now restart your Django Server.")
                         return
                    await asyncio.sleep(2)
                    print(".", end="", flush=True)
                
                print("\n❌ Timed out.")

    except Exception as e:
        print(f"\n(Note: Tool error expected if auth triggers: {e})")

if __name__ == "__main__":
    try:
        asyncio.run(run_auth())
    except KeyboardInterrupt:
        pass