"""
CurricuForge — AI Engine Test Suite
Run with: python test_ai_engine.py
"""

import json
from ai_engine import build_prompt, extract_json, validate_curriculum  # type: ignore

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def check(test_name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((test_name, status))
    print(f"{status} — {test_name}")
    if detail:
        print(f"       {detail}")


print("\n" + "=" * 55)
print("  CurricuForge AI Engine — Full Test Suite")
print("=" * 55)


# ─────────────────────────────────────────
# SECTION 1: build_prompt() TESTS
# ─────────────────────────────────────────
print("\n📋 SECTION 1: build_prompt()")
print("-" * 40)

# Test 1: Normal input
inputs = {"skill": "Machine Learning", "level": "BTech", "semesters": 4, "weekly_hours": 20, "industry": "AI"}
prompt = build_prompt(inputs)
check("Prompt is a string",                isinstance(prompt, str))
check("Prompt includes skill name",         "Machine Learning" in prompt)
check("Prompt includes level",              "BTech" in prompt)
check("Prompt includes semester count",     "4" in prompt)
check("Prompt includes industry",           "AI" in prompt)
check("Prompt demands JSON only",           "ONLY" in prompt and "JSON" in prompt)
check("Prompt has reasonable length",       len(prompt) > 500, f"Length: {len(prompt)} chars")

# Test 2: Different education levels
for level in ["Diploma", "Master's Degree", "Professional Certification"]:
    p = build_prompt({"skill": "Python", "level": level, "semesters": 2, "weekly_hours": 15, "industry": "Web"})
    check(f"Prompt works for level: {level}", level in p)

# Test 3: Weekly hours → courses per semester logic
low_hours  = build_prompt({"skill": "Python", "level": "Diploma", "semesters": 2, "weekly_hours": 10, "industry": "Web"})
high_hours = build_prompt({"skill": "Python", "level": "BTech",   "semesters": 4, "weekly_hours": 30, "industry": "AI"})
check("Low hours (10) → min 3 courses per sem",  "3" in low_hours)
check("High hours (30) → max 6 courses per sem", "6" in high_hours)

# Test 4: Missing optional fields use defaults
minimal = build_prompt({})
check("Empty input uses default skill",    "Machine Learning" in minimal)
check("Empty input uses default level",    "BTech" in minimal)


# ─────────────────────────────────────────
# SECTION 2: extract_json() TESTS
# ─────────────────────────────────────────
print("\n🔍 SECTION 2: extract_json()")
print("-" * 40)

valid_json_str = json.dumps({
    "curriculum_title": "ML BTech",
    "level": "BTech",
    "skill_domain": "Machine Learning",
    "total_semesters": 2,
    "semesters": [{"semester_number": 1, "courses": []}]
})

# Test 5: Clean JSON string
result = extract_json(valid_json_str)
check("Parses clean JSON directly",          result["curriculum_title"] == "ML BTech")

# Test 6: Markdown fenced with ```json
fenced = f"```json\n{valid_json_str}\n```"
result = extract_json(fenced)
check("Strips ```json fences correctly",     result["curriculum_title"] == "ML BTech")

# Test 7: Plain ``` fences (no language tag)
plain_fenced = f"```\n{valid_json_str}\n```"
result = extract_json(plain_fenced)
check("Strips plain ``` fences correctly",   result["curriculum_title"] == "ML BTech")

# Test 8: JSON buried in text
buried = f"Here is your curriculum: {valid_json_str} Hope this helps!"
result = extract_json(buried)
check("Extracts JSON buried in text",        result["curriculum_title"] == "ML BTech")

# Test 9: Extra whitespace and newlines
padded = f"\n\n   {valid_json_str}   \n\n"
result = extract_json(padded)
check("Handles extra whitespace/newlines",   result["curriculum_title"] == "ML BTech")

# Test 10: AI adds commentary before and after
commentary = f"Sure! Here you go:\n\n{valid_json_str}\n\nI hope this curriculum works for you!"
result = extract_json(commentary)
check("Handles AI commentary before/after", result["curriculum_title"] == "ML BTech")

# Test 11: Completely broken — should raise ValueError
try:
    extract_json("This is just plain text with no JSON at all.")
    check("Raises error on no JSON found",   False)
except ValueError:
    check("Raises error on no JSON found",   True)

# Test 12: Empty string
try:
    extract_json("")
    check("Raises error on empty string",    False)
except (ValueError, Exception):
    check("Raises error on empty string",    True)


# ─────────────────────────────────────────
# SECTION 3: validate_curriculum() TESTS
# ─────────────────────────────────────────
print("\n🛡️  SECTION 3: validate_curriculum()")
print("-" * 40)

def make_valid_curriculum(overrides={}):
    """Helper to build a base valid curriculum dict."""
    base = {
        "curriculum_title": "ML BTech Program",
        "level": "BTech",
        "skill_domain": "Machine Learning",
        "industry_focus": "AI",
        "total_semesters": 2,
        "weekly_hours": 20,
        "semesters": [
            {
                "semester_number": 1,
                "semester_title": "Foundation",
                "courses": [
                    {
                        "course_code": "CS101",
                        "course_name": "Intro to ML",
                        "credits": 4,
                        "hours_per_week": 3,
                        "description": "Introduction to machine learning concepts.",
                        "topics": ["Supervised Learning", "Unsupervised Learning", "Neural Networks"]
                    }
                ]
            }
        ],
        "capstone_project": {
            "title": "ML Final Project",
            "description": "Build a real-world ML application."
        }
    }
    base.update(overrides)
    return base

# Test 13: Valid curriculum passes without changes
valid = make_valid_curriculum()
result = validate_curriculum(valid)
check("Valid curriculum passes validation",  result["curriculum_title"] == "ML BTech Program")

# Test 14: Missing curriculum_title raises error
try:
    bad = make_valid_curriculum()
    del bad["curriculum_title"]  # type: ignore
    validate_curriculum(bad)
    check("Raises error on missing curriculum_title", False)
except ValueError:
    check("Raises error on missing curriculum_title", True)

# Test 15: Missing semesters raises error
try:
    bad = make_valid_curriculum()
    del bad["semesters"]  # type: ignore
    validate_curriculum(bad)
    check("Raises error on missing semesters",        False)
except ValueError:
    check("Raises error on missing semesters",        True)

# Test 16: Empty semesters list raises error
try:
    bad = make_valid_curriculum({"semesters": []})
    validate_curriculum(bad)
    check("Raises error on empty semesters list",     False)
except ValueError:
    check("Raises error on empty semesters list",     True)

# Test 17: Auto-fills missing course_code
no_code = make_valid_curriculum()
del no_code["semesters"][0]["courses"][0]["course_code"]  # type: ignore
result = validate_curriculum(no_code)
code = result["semesters"][0]["courses"][0]["course_code"]
check("Auto-fills missing course_code",      len(code) > 0, f"Generated: {code}")

# Test 18: Auto-fills missing credits with default 4
no_credits = make_valid_curriculum()
del no_credits["semesters"][0]["courses"][0]["credits"]  # type: ignore
result = validate_curriculum(no_credits)
check("Auto-fills missing credits → 4",      result["semesters"][0]["courses"][0]["credits"] == 4)

# Test 19: Auto-fills missing hours_per_week with default 3
no_hours = make_valid_curriculum()
del no_hours["semesters"][0]["courses"][0]["hours_per_week"]  # type: ignore
result = validate_curriculum(no_hours)
check("Auto-fills missing hours_per_week → 3", result["semesters"][0]["courses"][0]["hours_per_week"] == 3)

# Test 20: Auto-fills missing topics
no_topics = make_valid_curriculum()
del no_topics["semesters"][0]["courses"][0]["topics"]  # type: ignore
result = validate_curriculum(no_topics)
topics = result["semesters"][0]["courses"][0]["topics"]
check("Auto-fills missing topics list",      isinstance(topics, list) and len(topics) >= 3)

# Test 21: Extends topics list if less than 3
short_topics = make_valid_curriculum()
short_topics["semesters"][0]["courses"][0]["topics"] = ["Only one topic"]  # type: ignore
result = validate_curriculum(short_topics)
topics = result["semesters"][0]["courses"][0]["topics"]
check("Extends topics list to minimum 3",    len(topics) >= 3, f"Topics count: {len(topics)}")

# Test 22: Auto-fills missing description
no_desc = make_valid_curriculum()
del no_desc["semesters"][0]["courses"][0]["description"]  # type: ignore
result = validate_curriculum(no_desc)
desc = result["semesters"][0]["courses"][0]["description"]
check("Auto-fills missing description",      isinstance(desc, str) and len(desc) > 0)

# Test 23: Auto-adds capstone if missing
no_capstone = make_valid_curriculum()
del no_capstone["capstone_project"]  # type: ignore
result = validate_curriculum(no_capstone)
check("Auto-adds missing capstone_project",  "capstone_project" in result)

# Test 24: Semester with no courses raises error
try:
    no_courses = make_valid_curriculum()
    no_courses["semesters"][0]["courses"] = []  # type: ignore
    validate_curriculum(no_courses)
    check("Raises error on semester with no courses", False)
except ValueError:
    check("Raises error on semester with no courses", True)


# ─────────────────────────────────────────
# SECTION 4: EDGE CASES
# ─────────────────────────────────────────
print("\n⚠️  SECTION 4: Edge Cases")
print("-" * 40)

# Test 25: Minimum semesters (2)
p = build_prompt({"skill": "Python", "level": "Diploma", "semesters": 2, "weekly_hours": 10, "industry": "Web"})
check("Prompt works with minimum 2 semesters", "2" in p)

# Test 26: Maximum semesters (8)
p = build_prompt({"skill": "Data Science", "level": "Master's Degree", "semesters": 8, "weekly_hours": 30, "industry": "Data Science"})
check("Prompt works with maximum 8 semesters", "8" in p)

# Test 27: Special characters in skill name
p = build_prompt({"skill": "C++ & Algorithms", "level": "BTech", "semesters": 4, "weekly_hours": 20, "industry": "Systems"})
check("Handles special chars in skill name",  "C++" in p)

# Test 28: Multiple courses auto-code generation
multi_course = make_valid_curriculum()
multi_course["semesters"][0]["courses"] = [  # type: ignore
    {"course_name": f"Course {i}"} for i in range(4)
]
result = validate_curriculum(multi_course)
codes = [c["course_code"] for c in result["semesters"][0]["courses"]]
check("Auto-generates unique codes for 4 courses", len(set(codes)) == 4, f"Codes: {codes}")


# ─────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────
print("\n" + "=" * 55)
passed = sum(1 for _, s in results if s == PASS)
failed = sum(1 for _, s in results if s == FAIL)
total  = len(results)
print(f"  Results: {passed}/{total} passed   |   {failed} failed")
print("=" * 55)

if failed == 0:
    print("  🎉 All tests passed! ai_engine.py is working correctly.")
else:
    print("  ⚠️  Some tests failed. Review the ❌ items above.")
    print("\n  Failed tests:")
    for name, status in results:
        if status == FAIL:
            print(f"    • {name}")
print()