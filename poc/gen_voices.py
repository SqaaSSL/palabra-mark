"""Generates test greetings with ElevenLabs and Gemini into voices/. Reads keys from ../.env.
Usage: python3 gen_voices.py"""
import base64, json, os, subprocess, urllib.request, urllib.error

env = dict(l.strip().split("=", 1) for l in open(os.path.join(os.path.dirname(__file__), "..", ".env")) if "=" in l)
os.makedirs("voices", exist_ok=True)
EN = ["Hi, good morning. I'm calling for Ana Morales, about her delivery this week.",
      "Hello, this is the assistant of David Chen. I'm calling to move his appointment on Friday.",
      "Good afternoon. I'm calling on behalf of Priya Nair about the invoice you sent last month.",
      "Hi there, I'm an AI assistant calling for Tom Becker. He would like to cancel his subscription."]
ES = "Hola, buenos días. Llamo de parte de Ana Morales, por la entrega de esta semana."
HI = "Hello ji, main Priya Nair ki assistant bol rahi hoon. Unki delivery ke baare mein call kiya hai."
ELEVEN = [("EXAVITQu4vr4xnSDxMaL", "sarah", EN[0]), ("JBFqnCBsd6RMkjVDRZzb", "george", EN[1]), ("Xb7hH8MSUJpSbSDYk0k2", "alice", EN[2]),
          ("nPczCjzI2devNBz1zQrb", "brian", EN[3]), ("IKne3meq5aSn9XLyUdCD", "charlie", EN[0]), ("pqHfZKP75CvOlQylNhV4", "bill", EN[1]),
          ("Qvbf0AoA7UZSgJUp8Ba5", "mia-es", ES), ("ftDdhfYtmfGP0tFlBYA1", "alisha-hi", HI)]
GEMINI = [("Kore", EN[2]), ("Puck", EN[3]), ("Charon", EN[0]), ("Aoede", EN[1]), ("Fenrir", ES), ("Leda", HI)]

def post(url, headers, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    try: return urllib.request.urlopen(req, timeout=120).read()
    except urllib.error.HTTPError as e: raise RuntimeError(f"{e.code} {e.read()[:200]!r}")

for vid, name, text in ELEVEN:
    out = f"voices/el_{name}.mp3"
    if os.path.exists(out): continue
    try:
        open(out, "wb").write(post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128",
                                   {"xi-api-key": env["ELEVENLABS_API_KEY"]}, {"text": text, "model_id": "eleven_multilingual_v2"}))
        print("ok", out)
    except Exception as e: print("FAILED", out, e)

for voice, text in GEMINI:
    out = f"voices/gm_{voice.lower()}.wav"
    if os.path.exists(out): continue
    try:
        r = json.loads(post("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent",
                            {"x-goog-api-key": env["GEMINI_API_KEY"]},
                            {"contents": [{"parts": [{"text": "Say in a natural phone voice: " + text}]}],
                             "generationConfig": {"responseModalities": ["AUDIO"],
                                                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}))
        part = r["candidates"][0]["content"]["parts"][0]["inlineData"]
        rate = part["mimeType"].split("rate=")[-1] if "rate=" in part["mimeType"] else "24000"
        data = base64.b64decode(part["data"])
        if data[:4] == b"RIFF": open(out, "wb").write(data)            # already a WAV file
        else: subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", rate, "-ac", "1", "-i", "-", out], input=data, check=True)
        print("ok", out, part["mimeType"])
    except Exception as e: print("FAILED", out, str(e)[:300])
