import asyncio
import os
from dotenv import load_dotenv
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

load_dotenv()

USER_EMAIL = "abhilashkumarmishra713@gmail.com"

async def persistent_auth():
    print("\n=== PERSISTENT GOOGLE AUTH SETUP ===\n")
    
    env_vars = {
        **os.environ,
        "GOOGLE_CLIENT_SECRET_PATH": "credentials.json",
        "GOOGLE_OAUTH_CLIENT_ID": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        "GOOGLE_OAUTH_CLIENT_SECRET": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        "MCP_SINGLE_USER_MODE": "true",
        "USER_GOOGLE_EMAIL": USER_EMAIL
    }
    
    server_params = StdioServerParameters(
        command="workspace-mcp",
        args=[],
        env=env_vars
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("✅ MCP Server initialized")
            await session.initialize()
            
            print(f"\n🔐 Starting authentication for: {USER_EMAIL}\n")
            
            # Check credentials
            creds_dir = "/home/abhi/.google_workspace_mcp/credentials"
            if os.path.exists(creds_dir):
                files = os.listdir(creds_dir)
                print(f"📁 Credentials directory has {len(files)} file(s)")
            
            # Try to call the tool
            try:
                result = await session.call_tool(
                    "search_gmail_messages", 
                    {
                        "query": "label:inbox", 
                        "page_size": 1,
                        "user_google_email": USER_EMAIL
                    }
                )
                print("\n✅ ALREADY AUTHENTICATED!")
                print("📧 Gmail works! You're all set!")
                return
                
            except Exception as e:
                error_msg = str(e)
                
                # Only proceed if this is an auth error
                if "Authorization URL" not in error_msg:
                    print(f"\n❌ Unexpected error (not auth related):")
                    print(error_msg[:500])
                    return
                
                # Extract URL
                start = error_msg.find("https://accounts.google.com")
                if start == -1:
                    print("❌ Could not find auth URL in error message")
                    return
                
                temp = error_msg[start:]
                
                # Find end of URL
                end = len(temp)
                for delimiter in ["**", "\n", " LLM,", "Markdown"]:
                    pos = temp.find(delimiter)
                    if pos != -1 and pos < end:
                        end = pos
                
                auth_url = temp[:end].strip()
                
                print("\n" + "=" * 90)
                print("🔗 AUTHORIZATION REQUIRED - CLICK THIS LINK:")
                print("=" * 90)
                print(f"\n{auth_url}\n")
                print("=" * 90)
                print(f"\n📋 Instructions:")
                print(f"1. Ctrl+Click the URL above to open it")
                print(f"2. Sign in with: {USER_EMAIL}")
                print(f"3. Click 'Continue' and 'Allow' for all permissions")
                print(f"4. Wait for 'Authentication Successful' page in browser")
                print(f"5. Return to THIS terminal and press ENTER")
                print(f"\n⚠️  CRITICAL: Keep this terminal open! Don't close it!")
                print(f"⚠️  The OAuth server is running and waiting for the callback.\n")
                
                # THIS IS THE KEY - WAIT FOR USER INPUT
                input("👉 Press ENTER only AFTER you see 'Authentication Successful' in your browser: ")
                
                print("\n🔄 Verifying credentials...")
                await asyncio.sleep(3)
                
                # Check if credentials exist now
                if os.path.exists(creds_dir):
                    files = os.listdir(creds_dir)
                    print(f"\n📁 After auth, credentials directory has {len(files)} file(s):")
                    if files:
                        for f in files:
                            file_path = os.path.join(creds_dir, f)
                            size = os.path.getsize(file_path)
                            print(f"   ✓ {f} ({size} bytes)")
                    else:
                        print("   ❌ Still empty! The OAuth callback failed.")
                        print("\n🔍 Check the logs above for OAuth server errors")
                        print("   Common issues:")
                        print("   - Port 8000 already in use")
                        print("   - Firewall blocking localhost:8000")
                        print("   - Wrong client ID/secret")
                        return
                
                # Try the call again
                try:
                    result = await session.call_tool(
                        "search_gmail_messages", 
                        {
                            "query": "label:inbox", 
                            "page_size": 1,
                            "user_google_email": USER_EMAIL
                        }
                    )
                    print("\n🎉 SUCCESS! Authentication complete!")
                    print("📧 Gmail access verified!")
                    print("\n✅ You can now use your Django app!")
                    
                except Exception as verify_err:
                    print(f"\n❌ Still failing after auth:")
                    print(str(verify_err)[:500])

if __name__ == "__main__":
    try:
        asyncio.run(persistent_auth())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted! Auth may not be complete.")