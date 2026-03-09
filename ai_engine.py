"""
CurricuForge — AI Engine
Primary: Groq (multiple API keys, auto-rotate)
Fallback: OpenRouter
"""

import os
import re
import json
import requests
import time

# Load .env file automatically (keys stay in .env, not in code)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, fall back to env vars

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

# Groq — primary (multiple keys: comma-separated)
# export GROQ_API_KEY='gsk_key1,gsk_key2,gsk_key3'
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_KEYS    = [k.strip() for k in os.environ.get("GROQ_API_KEY", "").split(",") if k.strip()]

# OpenRouter — fallback
# export OPENROUTER_API_KEY='sk-or-...'
OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"
OPENROUTER_KEY   = os.environ.get("OPENROUTER_API_KEY", "")

TIMEOUT     = 90
MAX_RETRIES = 3

# Track which Groq key to use next (round-robin)
_groq_key_index = 0


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_prompt(user_inputs: dict) -> str:
    skill        = user_inputs.get("skill", "Software Engineering")
    level        = user_inputs.get("level", "BTech")
    semesters    = int(user_inputs.get("semesters", 4))
    weekly_hours = int(user_inputs.get("weekly_hours", 20))
    industry     = user_inputs.get("industry", skill)

    return f"""You are an expert curriculum designer. Generate a complete, detailed university curriculum.

STRICT RULES:
1. Respond with ONLY valid JSON — no markdown, no backticks, no explanation
2. Every field in the schema must be present
3. Generate EXACTLY {semesters} semesters
4. Each semester must have 4–6 courses
5. Each course must have 4–6 topics

CURRICULUM REQUEST:
- Skill/Domain: {skill}
- Education Level: {level}
- Number of Semesters: {semesters}
- Weekly Study Hours: {weekly_hours}
- Industry Focus: {industry}

REQUIRED JSON SCHEMA (output ONLY this, nothing else):
{{
  "curriculum_title": "string",
  "level": "{level}",
  "skill_domain": "{skill}",
  "industry_focus": "{industry}",
  "total_semesters": {semesters},
  "weekly_hours": {weekly_hours},
  "semesters": [
    {{
      "semester_number": 1,
      "semester_title": "string",
      "courses": [
        {{
          "course_code": "string (e.g. CS101)",
          "course_name": "string",
          "credits": 4,
          "hours_per_week": 3,
          "description": "string (2-3 sentences)",
          "topics": ["topic1", "topic2", "topic3", "topic4"]
        }}
      ]
    }}
  ],
  "capstone_project": {{
    "title": "string",
    "description": "string (3-4 sentences)"
  }}
}}

Output the JSON now:"""


# ══════════════════════════════════════════════════════════════════════════════
# GROQ CALLER (primary — round-robin keys)
# ══════════════════════════════════════════════════════════════════════════════

def _next_groq_key():
    """Get next Groq key in round-robin fashion."""
    global _groq_key_index
    if not GROQ_KEYS:
        return None
    key = GROQ_KEYS[_groq_key_index % len(GROQ_KEYS)]
    _groq_key_index += 1
    return key


def call_groq(prompt: str) -> tuple:
    """Call Groq API. Returns (response_text, backend_name). Tries all keys."""
    if not GROQ_KEYS:
        raise ConnectionError("No GROQ_API_KEY set")

    last_error = None
    for _ in range(len(GROQ_KEYS)):
        key = _next_groq_key()
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are a curriculum design expert. Output ONLY valid JSON. No markdown, no backticks, no explanation."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 8192,
        }
        try:
            r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=TIMEOUT)
            if r.status_code == 429:
                print(f"[AI Engine] Groq key {key[:8]}... rate-limited, trying next key")
                last_error = "Rate limited"
                continue
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
            if text:
                return text, f"Groq ({GROQ_MODEL})"
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                print(f"[AI Engine] Groq key rate-limited, rotating...")
                last_error = "Rate limited"
                continue
            raise
        except Exception as e:
            last_error = str(e)
            continue

    raise ConnectionError(f"All {len(GROQ_KEYS)} Groq keys exhausted. Last error: {last_error}")


# ══════════════════════════════════════════════════════════════════════════════
# OPENROUTER CALLER (fallback)
# ══════════════════════════════════════════════════════════════════════════════

def call_openrouter(prompt: str) -> tuple:
    """Call OpenRouter API. Returns (response_text, backend_name)."""
    if not OPENROUTER_KEY:
        raise ConnectionError("No OPENROUTER_API_KEY set")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://curricuforge.app",
        "X-Title": "CurricuForge",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a curriculum design expert. Output ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
    }
    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    if not text:
        raise ValueError("OpenRouter returned empty response")
    return text, f"OpenRouter ({OPENROUTER_MODEL})"


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED CALLER — Groq first, then OpenRouter
# ══════════════════════════════════════════════════════════════════════════════

def call_llm(prompt: str) -> tuple:
    """Try Groq (all keys), then OpenRouter. Returns (response, backend_name)."""
    errors = []

    # 1. Try Groq
    if GROQ_KEYS:
        try:
            return call_groq(prompt)
        except Exception as e:
            errors.append(f"Groq: {e}")
            print(f"[AI Engine] Groq failed: {e}")

    # 2. Fallback to OpenRouter
    if OPENROUTER_KEY:
        try:
            print("[AI Engine] Falling back to OpenRouter...")
            return call_openrouter(prompt)
        except Exception as e:
            errors.append(f"OpenRouter: {e}")
            print(f"[AI Engine] OpenRouter failed: {e}")

    # 3. Nothing available
    msg = "No AI backend available.\n"
    if not GROQ_KEYS:
        msg += "  • Set GROQ_API_KEY: export GROQ_API_KEY='gsk_key1,gsk_key2'\n"
    if not OPENROUTER_KEY:
        msg += "  • Set OPENROUTER_API_KEY: export OPENROUTER_API_KEY='sk-or-...'\n"
    if errors:
        msg += f"\nErrors: {'; '.join(errors)}"
    raise ConnectionError(msg)


# ══════════════════════════════════════════════════════════════════════════════
# CHAT CALLER — for the chatbot (also Groq → OpenRouter)
# ══════════════════════════════════════════════════════════════════════════════

def chat_with_llm(user_message: str, history: list, system_prompt: str) -> tuple:
    """Chat mode: Groq first, then OpenRouter. Returns (response, backend_name)."""
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-10:]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_message})

    errors = []

    # 1. Groq
    if GROQ_KEYS:
        key = _next_groq_key()
        try:
            r = requests.post(GROQ_URL, headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }, json={
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 1024,
            }, timeout=TIMEOUT)
            if r.status_code != 429:
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"], "Groq"
            errors.append("Groq rate-limited")
        except Exception as e:
            errors.append(f"Groq: {e}")

    # 2. OpenRouter
    if OPENROUTER_KEY:
        try:
            r = requests.post(OPENROUTER_URL, headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://curricuforge.app",
                "X-Title": "CurricuForge",
            }, json={
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 1024,
            }, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"], "OpenRouter"
        except Exception as e:
            errors.append(f"OpenRouter: {e}")

    return f"❌ No AI backend responded.\nErrors: {'; '.join(errors)}", "none"


# ══════════════════════════════════════════════════════════════════════════════
# JSON EXTRACTOR
# ══════════════════════════════════════════════════════════════════════════════

def extract_json(raw: str) -> dict:
    # 1. Direct parse
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3. Extract outermost JSON object
    match = re.search(r"\{.*", raw, re.DOTALL)
    if match:
        json_str = match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # 4. Repair truncated JSON — close open brackets/braces
        repaired = _repair_truncated_json(json_str)
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Could not extract JSON from response:\n{raw[:500]}")


def _repair_truncated_json(s):
    """Try to fix truncated JSON by closing unclosed brackets and braces."""
    s = s.rstrip()

    # Remove trailing incomplete string (not closed quote)
    if s.count('"') % 2 != 0:
        last_quote = s.rfind('"')
        if last_quote > 0:
            s = s[0:last_quote + 1]

    # Remove trailing comma or colon
    s = s.rstrip().rstrip(',').rstrip(':')

    # Remove any incomplete key-value pair after last comma
    last_complete = max(s.rfind('}'), s.rfind(']'), s.rfind('"'))
    if last_complete > 0:
        s = s[0:last_complete + 1]

    # Count unclosed brackets
    open_braces = s.count('{') - s.count('}')
    open_brackets = s.count('[') - s.count(']')

    if open_braces < 0 or open_brackets < 0:
        return None

    # Close them
    s += ']' * open_brackets
    s += '}' * open_braces

    return s


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATOR
# ══════════════════════════════════════════════════════════════════════════════

def validate_curriculum(data: dict) -> dict:
    data.setdefault("curriculum_title", "Generated Curriculum")
    data.setdefault("level", "BTech")
    data.setdefault("skill_domain", "General")
    data.setdefault("industry_focus", "Technology")
    data.setdefault("total_semesters", len(data.get("semesters", [])))
    data.setdefault("weekly_hours", 20)
    data.setdefault("semesters", [])
    data.setdefault("capstone_project", {"title": "Final Project", "description": "Capstone project."})

    for i, sem in enumerate(data["semesters"]):
        sem.setdefault("semester_number", i + 1)
        sem.setdefault("semester_title", f"Semester {i + 1}")
        sem.setdefault("courses", [])
        for j, course in enumerate(sem["courses"]):
            course.setdefault("course_code", f"C{i+1}{j+1:02d}")
            course.setdefault("course_name", f"Course {j + 1}")
            course.setdefault("credits", 4)
            course.setdefault("hours_per_week", 3)
            course.setdefault("description", "")
            course.setdefault("topics", [])
    return data


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — generate_curriculum()
# ══════════════════════════════════════════════════════════════════════════════

def generate_curriculum(user_inputs: dict) -> dict:
    if not GROQ_KEYS and not OPENROUTER_KEY:
        return {
            "success": False,
            "error": (
                "No API keys configured.\n"
                "Set at least one:\n"
                "  export GROQ_API_KEY='gsk_key1,gsk_key2'\n"
                "  export OPENROUTER_API_KEY='sk-or-...'"
            ),
        }

    prompt = build_prompt(user_inputs)
    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n[AI Engine] Attempt {attempt}/{MAX_RETRIES}...")
        try:
            if attempt > 1:
                prompt_with_hint = (
                    "IMPORTANT: Return ONLY raw JSON. No markdown. No explanation.\n\n" + prompt
                )
            else:
                prompt_with_hint = prompt

            raw, backend = call_llm(prompt_with_hint)
            print(f"[AI Engine] Response from {backend} ({len(raw)} chars)")

            data = extract_json(raw)
            print("[AI Engine] JSON extracted successfully.")

            validated = validate_curriculum(data)
            print("[AI Engine] Curriculum validated.")

            return {"success": True, "curriculum": validated, "backend": backend}

        except (ConnectionError, TimeoutError) as e:
            return {"success": False, "error": str(e)}

        except (ValueError, KeyError) as e:
            last_error = str(e)
            print(f"[AI Engine] Attempt {attempt} failed: {last_error}")
            time.sleep(1)

        except Exception as e:
            last_error = str(e)
            print(f"[AI Engine] Unexpected error: {last_error}")

    return {"success": False, "error": f"Failed after {MAX_RETRIES} attempts. {last_error}"}


# ══════════════════════════════════════════════════════════════════════════════
# STATUS CHECK
# ══════════════════════════════════════════════════════════════════════════════

def get_backend_status() -> dict:
    """Return status of available backends for UI display."""
    return {
        "groq_keys": len(GROQ_KEYS),
        "groq_available": len(GROQ_KEYS) > 0,
        "openrouter_available": bool(OPENROUTER_KEY),
        "any_available": len(GROQ_KEYS) > 0 or bool(OPENROUTER_KEY),
    }


# ══════════════════════════════════════════════════════════════════════════════
# QUICK TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    status = get_backend_status()
    print("=" * 50)
    print("CurricuForge AI Engine — Status")
    print(f"  Groq keys:   {status['groq_keys']}")
    print(f"  OpenRouter:  {'✅' if status['openrouter_available'] else '❌'}")
    print("=" * 50)

    if not status["any_available"]:
        print("\n❌ No API keys set. Run:")
        print("  export GROQ_API_KEY='gsk_your_key'")
        print("  export OPENROUTER_API_KEY='sk-or-your_key'")
    else:
        print("\n🚀 Testing curriculum generation...")
        result = generate_curriculum({
            "skill": "Machine Learning",
            "level": "BTech",
            "semesters": 4,
            "weekly_hours": 20,
            "industry": "AI/Tech",
        })
        if result["success"]:
            cur = result["curriculum"]
            print(f"\n✅ Success via {result['backend']}")
            print(f"   Title:     {cur['curriculum_title']}")
            print(f"   Semesters: {len(cur['semesters'])}")
        else:
            print(f"\n❌ Failed: {result['error']}")