import os
import re
import sys
import json
import base64
import aiohttp
import asyncio
import tempfile
import edge_tts
import traceback
from google import genai
from pathlib import Path
from datetime import datetime
from google.genai import types
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from google.api_core.exceptions import ResourceExhausted

STT_MODEL = WhisperModel("tiny.en", device="cpu", compute_type="int8")

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

API_KEY = os.getenv("GEMINI_KEY")
USER_EMAIL = os.getenv("USER_GOOGLE_EMAIL")
CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
CREDENTIALS_DIR = Path.home() / ".google_workspace_mcp" / "credentials"
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "abhi-afk-dev")
MODEL_NAME = "gemini-2.5-flash"

CURRENT_PYTHON = Path(sys.executable)
EXECUTABLE = CURRENT_PYTHON.parent / "workspace-mcp"
if not EXECUTABLE.exists():
    EXECUTABLE = Path("/home/abhi/projects/Kaito_Web/env/bin/workspace-mcp")

DDG_EXECUTABLE = "/home/abhi/projects/Kaito_Web/env/bin/duckduckgo-mcp-server"

print(f"✅ KAITO ULTIMATE ACTIVE")

async def send_discord_message(message: str):
    token = os.getenv("DISCORD_BOT_TOKEN")
    channel_id = os.getenv("DISCORD_CHANNEL_ID")
    
    if not token or not channel_id:
        return "Error: Discord Token or Channel ID is missing in .env"

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    payload = {"content": message}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as res:
                if res.status == 200:
                    return "Notification sent successfully."
                else:
                    return f"Failed to send Discord message: {res.status} - {await res.text()}"
    except Exception as e:
        return f"Connection Error: {str(e)}"

def clean_schema(schema):
    if not isinstance(schema, dict): return schema
    cleaned = schema.copy()
    for key in ["additionalProperties", "title", "const", "default", "examples", "$schema"]:
        cleaned.pop(key, None)
    if "type" in cleaned and isinstance(cleaned["type"], list):
        valid = [t for t in cleaned["type"] if t != "null"]
        cleaned["type"] = valid[0] if valid else "string"
    if "required" in cleaned and isinstance(cleaned["required"], list):
        cleaned["required"] = [r for r in cleaned["required"] if r != "user_google_email"]
        if not cleaned["required"]: cleaned.pop("required")
    if "properties" in cleaned:
        for k, v in cleaned["properties"].items():
            cleaned["properties"][k] = clean_schema(v)
    if "items" in cleaned:
        if isinstance(cleaned["items"], dict):
            cleaned["items"] = clean_schema(cleaned["items"])
        elif isinstance(cleaned["items"], list):
            cleaned["items"] = [clean_schema(i) for i in cleaned["items"]]
    for logic in ["anyOf", "allOf", "oneOf"]:
        if logic in cleaned:
             cleaned[logic] = [clean_schema(item) for item in cleaned[logic]]
    return cleaned

async def determine_intent(user_query):
    try:
        client = genai.Client(api_key=API_KEY)
        
        prompt = f"""
        Classify this request: "{user_query}"
        
        ONLY select categories that are EXPLICITLY needed.
        
        - MAIL: Only if user mentions "email", "gmail", "draft", "send", "inbox".
        - CALENDAR: Only if user mentions "schedule", "event", "meeting", "calendar".
        - DRIVE: Only if user mentions "drive", "file", "doc", "sheet", "folder".
        - TASKS: Only if user mentions "task", "todo", "list".
        - WEB: General knowledge, news, facts, "DeepSeek", "who is", "why is", "search".
        - GITHUB: "repo", "code", "issue", "pull request", "PR", "commit", "branch".
        - DISCORD: "discord", "message", "notify", "ping".

        Return JSON list. Examples:
        "Why is sky blue?" -> ["WEB"]
        "Check my emails" -> ["MAIL"]
        """
        response = await client.aio.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except:
        return ["WEB"]

async def run_workspace_agent(user_query):
    intents = await determine_intent(user_query)
    print(f"🤖 ROUTER: {intents}")
    
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    
    workspace_keywords = ["mail", "email", "inbox", "sent", "calendar", "event", "schedule", "drive", "doc", "file", "sheet", "task", "todo"]
    github_keywords = ["repo", "code", "branch", "commit", "pr", "pull request", "issue", "github"]
    discord_kw = ["discord", "message", "notify", "ping"]

    query_lower = user_query.lower()
    has_workspace_kw = any(kw in query_lower for kw in workspace_keywords)
    has_github_kw = any(kw in query_lower for kw in github_keywords)

    if "GITHUB" in intents or has_github_kw:
        active_mode = "GITHUB"
    elif "DISCORD" in intents or any(k in query_lower for k in discord_kw):
        active_mode = "DISCORD" 
    elif any(i in ["MAIL", "CALENDAR", "DRIVE", "TASKS"] for i in intents) or has_workspace_kw:
        active_mode = "WORKSPACE"
    else:
        active_mode = "WEB"

    mcp_env = os.environ.copy()
    
    gh_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN")
    if gh_token:
        mcp_env["GITHUB_PERSONAL_ACCESS_TOKEN"] = gh_token
    
    mcp_env.update({
        "CREDENTIALS_DIR": str(CREDENTIALS_DIR),
        "USER_GOOGLE_EMAIL": USER_EMAIL,
        "MCP_SINGLE_USER_MODE": "true",
        "GOOGLE_OAUTH_CLIENT_ID": CLIENT_ID,
        "GOOGLE_OAUTH_CLIENT_SECRET": CLIENT_SECRET,
    })

    if active_mode == "GITHUB":
        print(f"🐙 Launching GitHub Server for {GITHUB_USERNAME}...")
        command = "npx"
        args = ["-y", "@modelcontextprotocol/server-github"]
        
        active_instruction = (
            f"You are Kaito in CODING MODE. Act for GitHub user '{GITHUB_USERNAME}'. "
            f"Current Repo Context: When user asks about a repo, assume owner is '{GITHUB_USERNAME}'. "
            "CRITICAL FILE READING RULES:"
            "1. If 'get_file_contents' fails with 'Not Found', immediately try 'list_directory_contents'."
            "2. Check for case sensitivity."
        )
        allowed_keywords = ["github", "issue", "pull_request", "repo", "file", "search", "commit", "push"]

    elif active_mode == "DISCORD":
        print("💬 Launching Discord Mode...")
        command = str(EXECUTABLE) 
        args = []
        active_instruction = "You are Kaito. Use 'send_discord_message' for Discord notifications."
        allowed_keywords = [] 
        
    elif active_mode == "WEB":
        print("🌍 Launching DuckDuckGo Server...")
        command = DDG_EXECUTABLE
        args = []
        active_instruction = f"You are Kaito. Today is {date_str}. Use 'search' to find info."
        allowed_keywords = ["search", "duckduckgo"]

    else:
        print("SVG Launching Workspace Server...")
        command = str(EXECUTABLE)
        args = []
        active_instruction = f"You are Kaito. Act for {USER_EMAIL}."
        allowed_keywords = ["gmail", "calendar", "drive", "task", "contact"]

    server_params = StdioServerParameters(command=command, args=args, env=mcp_env)

    try:
        client = genai.Client(api_key=API_KEY)

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:

                    await session.initialize()
                    tools_result = await session.list_tools()
                    
                    gemini_tools = []
            
                    if active_mode != "DISCORD":
                        for tool in tools_result.tools:
                            if any(k in tool.name.lower() for k in allowed_keywords):
                                if "search_custom" in tool.name.lower(): continue 
                                gemini_tools.append({
                                    "name": tool.name,
                                    "description": tool.description[:500],
                                    "parameters": clean_schema(tool.inputSchema)
                                })
                    
                    if active_mode == "DISCORD":
                            gemini_tools.append({
                                "name": "send_discord_message",
                                "description": "Sends a message to the user's Discord channel.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "message": {"type": "string", "description": "The text to send."}
                                    },
                                    "required": ["message"]
                                }
                            })

                    final_tools = {t['name']: t for t in gemini_tools}.values()
                    final_tools = list(final_tools)[:60]
                    
                    print(f"🛠️  Loaded {len(final_tools)} tools for {active_mode}")

                    tool_obj = types.Tool(function_declarations=final_tools) if final_tools else None
                    
                    chat = client.aio.chats.create(
                        model=MODEL_NAME,
                        config=types.GenerateContentConfig(
                            tools=[tool_obj] if tool_obj else None,
                            tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode="AUTO")) if tool_obj else None,
                            system_instruction=active_instruction
                        )
                    )

                    response = await chat.send_message(user_query)
                    
                    while response.function_calls:
                        for call in response.function_calls:
                            print(f"🚀 EXEC: {call.name}")
                            args = call.args or {}
                            
                            tool_output = {}

                            if call.name == "send_discord_message":
                                print("🔹 Executing Locally (Discord)")
                                try:
                                    result_text = await send_discord_message(args.get("message", ""))
                                    tool_output = {"result": result_text}
                                except Exception as e:
                                    tool_output = {"error": str(e)}
                            
                            else:
                                if active_mode == "GITHUB":
                                    if "repo" in args and "/" in args["repo"]:
                                        parts = args["repo"].split("/")
                                        if len(parts) == 2:
                                            args["owner"] = parts[0]
                                            args["repo"] = parts[1]
                                    
                                    gh_user = os.getenv("GITHUB_USERNAME")
                                    if "owner" not in args and gh_user:
                                        args["owner"] = gh_user
                                    
                                    if "path" in args and args["path"].startswith("/"):
                                        args["path"] = args["path"].lstrip("/")                            
                                    
                                    print(f"🔹 DEBUG GITHUB ARGS: {args}")

                                elif active_mode == "WORKSPACE":
                                     args["user_google_email"] = USER_EMAIL

                                try:
                                    result = await session.call_tool(call.name, args)
                                    content = result.content
                                    if isinstance(content, list):
                                        text_content = " ".join([c.text for c in content if hasattr(c, 'text')])
                                    else:
                                        text_content = str(content)
                                    
                                    tool_output = {"result": text_content[:5000]}

                                except Exception as e:
                                    print(f"⚠️ Remote Tool Failed: {e}")
                                    tool_output = {"error": str(e), "hint": "Check Auth Token or Params."}
                            
                            response = await chat.send_message(
                                message=types.Part(
                                    function_response=types.FunctionResponse(
                                        name=call.name,
                                        response=tool_output
                                    )
                                )
                            )
                    
                    return response.text

    except Exception as e:
        traceback.print_exc()
        return f"Core Error: {str(e)}"

def transcribe_audio(audio_file) -> str:
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            for chunk in audio_file.chunks():
                temp_audio.write(chunk)
            temp_path = temp_audio.name

        segments, info = STT_MODEL.transcribe(temp_path, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        
        os.remove(temp_path)
        return text.strip()
    except Exception as e:
        print(f"❌ STT Error: {e}")
        return ""

async def generate_audio(text: str) -> str:
    print(f"🔊 [TTS] Starting generation for: '{text[:30]}...'")    
    clean_text = re.sub(r'[*_`]', '', text) 
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            temp_path = temp_audio.name
        
        communicate = edge_tts.Communicate(clean_text, "en-US-ChristopherNeural")
        await communicate.save(temp_path)
        
        file_size = os.path.getsize(temp_path)
        print(f"🔊 [TTS] File saved at {temp_path} | Size: {file_size} bytes")
        
        if file_size == 0:
            print("❌ [TTS] Critical Error: Generated audio file is empty!")
            return None

        with open(temp_path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode("utf-8")
        
        print(f"✅ [TTS] Encoded Base64 Length: {len(audio_data)}")
        
        os.remove(temp_path)
        return audio_data

    except Exception as e:
        print(f"❌ [TTS] Exception: {e}")
        traceback.print_exc()
        return None

@csrf_exempt
async def interface(request):
    query = ""
    audio_base64 = None

    if request.method == "POST":
        try:
            if request.content_type.startswith("multipart/form-data"):
                if 'audio' in request.FILES:
                    print("🎤 [STT] Receiving Audio File...")
                    query = transcribe_audio(request.FILES['audio'])
                    print(f"📝 [STT] Transcribed: '{query}'")
                elif 'text' in request.POST:
                    query = request.POST.get('text')
            else:
                data = json.loads(request.body)
                query = data.get("prompt", "")

            if not query:
                return JsonResponse({"error": "No input provided"})

            print(f"\n📨 USER: '{query}'")
            
            reply_text = await run_workspace_agent(query)
            
            if reply_text and len(reply_text) < 2000:
                audio_base64 = await generate_audio(reply_text)
            else:
                print("⚠️ [TTS] Skipped: Response too long or empty.")

            return JsonResponse({
                "reply": reply_text,
                "audio": audio_base64
            })

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"reply": f"Error: {str(e)}"})

    return JsonResponse({"error": "POST required"})