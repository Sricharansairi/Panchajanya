"""
CurricuForge — AI-Powered Curriculum Generation Platform
Streamlit UI | Groq (primary) + OpenRouter (fallback)
Features: Generator, Analytics, History, Chat, Study Planner, Skill Gap, Job Mapping
"""

import streamlit as st  # type: ignore
import json
import time
import os
import hashlib
from datetime import datetime, date
import plotly.graph_objects as go  # type: ignore
import plotly.express as px  # type: ignore
from typing import Dict, Any, List

# ── Module imports ────────────────────────────────────────────────────────────
try:
    from ai_engine import (  # type: ignore
        generate_curriculum,
        chat_with_llm,
        get_backend_status,
        GROQ_KEYS,
        GROQ_MODEL,
    )

    AI_ENGINE_AVAILABLE = True
except ImportError:
    AI_ENGINE_AVAILABLE = False

    def get_backend_status():
        return {
            "groq_keys": 0,
            "openrouter_available": False,
            "any_available": False,
        }

    GROQ_KEYS = []
    GROQ_MODEL = ""

try:
    from pdf_generator import generate_pdf, generate_text_pdf  # type: ignore

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    generate_text_pdf = None

try:
    from json_exporter import export_all  # type: ignore

    JSON_EXPORTER_AVAILABLE = True
except ImportError:
    JSON_EXPORTER_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="CurricuForge",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)
HISTORY_DIR = os.path.join(os.path.dirname(__file__), "curriculum_history")
os.makedirs(HISTORY_DIR, exist_ok=True)

CHAT_SYSTEM_PROMPT = (
    "You are CurricuForge Assistant, an AI expert in education and curriculum design. "
    "Help with course planning, skill development, learning paths, syllabus design, "
    "education levels, industry trends, and academic best practices. "
    "Keep answers concise and well-structured. Use bullet points when listing items."
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
<style>
[data-testid="stToolbar"]   { display: none !important; }
[data-testid="stDecoration"]{ display: none !important; }
#MainMenu                   { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
footer { visibility: hidden !important; }
.viewerBadge_container { display: none !important; }
.stDeployButton { display: none !important; }
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stSelectbox"] > div > div:focus-within {
    border-color: #6B4EFF !important;
    box-shadow: 0 0 0 2px rgba(107,78,255,0.2) !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
_DEFAULTS = {
    "current_page": "Home",
    "curriculum_result": None,
    "curriculum_error": None,
    "dismiss_warnings": False,
    "p_skill": "",
    "p_level": "BTech",
    "p_semesters": 4,
    "p_hours": 20,
    "p_industry": "",
    "p_type": None,
    "p_language": "English",
    "p_skill_gap": False,
    "p_current_skills": "",
    "chat_history": [],
    "curriculum_chat_context": None,
    "compare_result": None,
    "study_plan": None,
    "job_mapping": None,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ══════════════════════════════════════════════════════════════════════════════
# WARNINGS
# ══════════════════════════════════════════════════════════════════════════════
_SEM_RANGE: Dict[str, tuple[int, int]] = {
    "Diploma": (2, 4),
    "BTech": (4, 8),
    "Master's Degree": (2, 4),
    "Professional Certification": (2, 3),
}
_HR_RANGE: Dict[str, tuple[int, int]] = {
    "Diploma": (10, 25),
    "BTech": (15, 30),
    "Master's Degree": (15, 35),
    "Professional Certification": (10, 20),
}


def _get_warnings(level, semesters, weekly_hours):
    out = []
    slo, shi = _SEM_RANGE.get(level, (2, 8))
    if semesters < slo or semesters > shi:
        out.append(
            f"**{level}** typically has **{slo}–{shi}** semesters — you chose **{semesters}**."
        )
    hlo, hhi = _HR_RANGE.get(level, (10, 40))
    if weekly_hours < hlo or weekly_hours > hhi:
        out.append(
            f"**{level}** typically needs **{hlo}–{hhi} hrs/week** — you entered **{weekly_hours}**."
        )
    return out


# ══════════════════════════════════════════════════════════════════════════════
# HISTORY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def _save_to_history(curriculum):
    title = curriculum.get("curriculum_title", "Untitled")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = (
        "".join(c if c.isalnum() or c in "_ " else "" for c in title)[:30]  # type: ignore
        .strip()
        .replace(" ", "_")
    )
    filename = f"{ts}_{safe}.json"
    filepath = os.path.join(HISTORY_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(
            {
                "curriculum": curriculum,
                "saved_at": datetime.now().isoformat(),
                "title": title,
            },
            f,
            indent=2,
        )
    return filepath


def _load_history():
    items = []
    if not os.path.exists(HISTORY_DIR):
        return items
    for fname in sorted(os.listdir(HISTORY_DIR), reverse=True):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(HISTORY_DIR, fname)) as f:
                    data = json.load(f)
                data["_filename"] = fname
                items.append(data)
            except Exception:
                pass
    return items


def _delete_history_item(filename):
    path = os.path.join(HISTORY_DIR, filename)
    if os.path.exists(path):
        os.remove(path)


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _compute_analytics(cur):
    semesters = cur.get("semesters", [])
    stats: Dict[str, Any] = {
        "total_courses": 0,
        "total_credits": 0,
        "total_topics": 0,
        "sem_names": [],
        "sem_courses": [],
        "sem_credits": [],
        "sem_hours": [],
        "all_topics": [],
        "course_names": [],
        "course_credits": [],
    }
    for sem in semesters:
        courses = sem.get("courses", [])
        sem_credits = sum(c.get("credits", 4) for c in courses)
        sem_hours = sum(c.get("hours_per_week", 3) for c in courses)
        stats["sem_names"].append(f"Sem {sem.get('semester_number', '')}")
        stats["sem_courses"].append(len(courses))
        stats["sem_credits"].append(sem_credits)
        stats["sem_hours"].append(sem_hours)
        stats["total_courses"] += len(courses)
        stats["total_credits"] += sem_credits
        for c in courses:
            stats["total_topics"] += len(c.get("topics", []))
            stats["all_topics"].extend(c.get("topics", []))
            stats["course_names"].append(c.get("course_name", ""))
            stats["course_credits"].append(c.get("credits", 4))
    return stats


# ══════════════════════════════════════════════════════════════════════════════
# CURRICULUM SUMMARY (for chatbot)
# ══════════════════════════════════════════════════════════════════════════════
def _build_curriculum_summary(cur):
    lines = [
        f"Curriculum: {cur.get('curriculum_title','')}",
        f"Level: {cur.get('level','')}",
        "",
    ]
    for sem in cur.get("semesters", []):
        lines.append(
            f"Semester {sem.get('semester_number','')}: {sem.get('semester_title','')}"
        )
        for c in sem.get("courses", []):
            lines.append(
                f"  • {c.get('course_code','')} — {c.get('course_name','')}"
            )
            if c.get("topics"):
                lines.append(f"    Topics: {', '.join(c['topics'])}")
        lines.append("")
    cap = cur.get("capstone_project", {})
    if cap:
        lines.append(f"Capstone: {cap.get('title','')}")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# RENDER CURRICULUM
# ══════════════════════════════════════════════════════════════════════════════
def _render_curriculum(cur, show_export=True):
    st.header(cur.get("curriculum_title", "Curriculum"))
    m1, m2, m3 = st.columns(3)
    m1.write(f"🎓 **Level:** {cur.get('level', '—')}")
    m2.write(f"📚 **Domain:** {cur.get('skill_domain', '—')}")
    m3.write(f"🏭 **Industry:** {cur.get('industry_focus', '—')}")
    m4, m5, _ = st.columns(3)
    m4.write(f"📅 **Semesters:** {cur.get('total_semesters', '—')}")
    m5.write(f"⏰ **Hours/Week:** {cur.get('weekly_hours', '—')}")

    # Mini analytics
    stats = _compute_analytics(cur)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Courses", stats["total_courses"])
    k2.metric("Total Credits", stats["total_credits"])
    k3.metric("Total Topics", stats["total_topics"])
    k4.metric(
        "Avg. Credits / Sem",
        f"{float(stats['total_credits']) / max(len(stats['sem_names']), 1):.1f}"
    )
    st.subheader("📋 Semester Breakdown")

    for sem in cur.get("semesters", []):
        courses = sem.get("courses", [])
        with st.expander(
            f"Semester {sem.get('semester_number','')}: {sem.get('semester_title','')}  —  {len(courses)} courses",
            expanded=True,
        ):
            for row_start in range(0, len(courses), 3):
                row = courses[row_start : row_start + 3]
                cols = st.columns(3)
                for j, c in enumerate(row):
                    with cols[j]:
                        with st.container(border=True):
                            st.caption(c.get("course_code", ""))
                            st.markdown(f"**{c.get('course_name', '')}**")
                            st.write(
                                f"📘 {c.get('credits', '4')} Credits  ·  ⏱️ {c.get('hours_per_week', '3')}h/week"
                            )
                            if c.get("description"):
                                st.write(c["description"])
                            if c.get("topics"):
                                st.caption("**Topics**")
                                st.write(" · ".join(c["topics"]))
    st.divider()

    cap = cur.get("capstone_project", {})
    if cap:
        st.subheader("🏆 Capstone Project")
        with st.container(border=True):
            st.markdown(f"**{cap.get('title', 'Capstone')}**")
            if cap.get("description"):
                st.write(cap["description"])
        st.divider()

    if not show_export:
        return

    # Export & AI Actions
    st.subheader("📥 Export & AI Actions")
    safe = cur.get("curriculum_title", "curriculum").replace(" ", "_")[:40]
    e1, e2, e3 = st.columns(3)
    with e1:
        if PDF_AVAILABLE:
            try:
                st.download_button(
                    "⬇ PDF Syllabus",
                    generate_pdf(cur),
                    f"{safe}.pdf",
                    "application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"PDF failed: {e}")
        else:
            st.info("pdf_generator.py not found")
    with e2:
        st.download_button(
            "⬇ JSON Data",
            json.dumps(cur, indent=2, ensure_ascii=False),
            f"{safe}.json",
            "application/json",
            use_container_width=True,
        )
    with e3:
        if st.button(
            "💬 Ask Doubts", key="ask_doubts", use_container_width=True
        ):
            st.session_state.curriculum_chat_context = cur
            st.session_state.current_page = "Chat"
            st.rerun()

    # AI-powered extras
    st.divider()
    st.subheader("🤖 AI-Powered Tools")
    t1, t2, t3 = st.columns(3)

    with t1:
        if st.button(
            "📅 Generate Study Plan",
            key="gen_study_plan",
            use_container_width=True,
        ):
            with st.spinner("Creating study plan..."):
                summary = _build_curriculum_summary(cur)
                prompt = (
                    f"Based on this curriculum:\n\n{summary}\n\n"
                    f"Create a detailed WEEKLY study plan for Semester 1. "
                    f"Total weekly hours: {cur.get('weekly_hours', 20)}. "
                    f"For each day (Monday-Saturday), allocate specific courses and topics. "
                    f"Include study tips and break suggestions. Format as a clear schedule."
                )
                response, backend = chat_with_llm(
                    prompt,
                    [],
                    "You are a study planning expert. Create detailed, actionable study schedules.",
                )
                st.session_state.study_plan = response

    with t2:
        if st.button(
            "💼 Map to Job Roles", key="gen_job_map", use_container_width=True
        ):
            with st.spinner("Mapping to industry roles..."):
                summary = _build_curriculum_summary(cur)
                prompt = (
                    f"Based on this curriculum:\n\n{summary}\n\n"
                    f"Map each semester's courses to specific INDUSTRY JOB ROLES. "
                    f"For each role, list: Job Title, Required courses from this curriculum, "
                    f"Expected salary range (India), Companies hiring. "
                    f"Cover at least 6-8 job roles. Format clearly with headers."
                )
                response, backend = chat_with_llm(
                    prompt,
                    [],
                    "You are a career counseling expert. Map educational curricula to real industry job roles.",
                )
                st.session_state.job_mapping = response

    with t3:
        if st.button(
            "💾 Save to History", key="save_hist", use_container_width=True
        ):
            path = _save_to_history(cur)
            st.success(f"✅ Saved! View in History tab.")

    # Show study plan if generated
    if st.session_state.get("study_plan"):
        st.divider()
        st.subheader("📅 Weekly Study Plan (Semester 1)")
        with st.container(border=True):
            st.write(st.session_state.study_plan)
        sp1, sp2 = st.columns(2)
        with sp1:
            if PDF_AVAILABLE and generate_text_pdf:
                try:
                    sp_pdf = generate_text_pdf(
                        "Weekly Study Plan",
                        st.session_state.study_plan,
                        subtitle=cur.get("curriculum_title", ""),
                    )
                    st.download_button(
                        "⬇ Download Study Plan PDF",
                        sp_pdf,
                        f"{safe}_study_plan.pdf",
                        "application/pdf",
                        key="dl_sp_pdf",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"PDF failed: {e}")
        with sp2:
            if st.button(
                "✕ Close Study Plan", key="close_sp", use_container_width=True
            ):
                st.session_state.study_plan = None
                st.rerun()

    # Show job mapping if generated
    if st.session_state.get("job_mapping"):
        st.divider()
        st.subheader("💼 Industry Job Role Mapping")
        with st.container(border=True):
            st.write(st.session_state.job_mapping)
        jm1, jm2 = st.columns(2)
        with jm1:
            if PDF_AVAILABLE and generate_text_pdf:
                try:
                    jm_pdf = generate_text_pdf(
                        "Industry Job Role Mapping",
                        st.session_state.job_mapping,
                        subtitle=cur.get("curriculum_title", ""),
                    )
                    st.download_button(
                        "⬇ Download Job Mapping PDF",
                        jm_pdf,
                        f"{safe}_job_mapping.pdf",
                        "application/pdf",
                        key="dl_jm_pdf",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"PDF failed: {e}")
        with jm2:
            if st.button(
                "✕ Close Job Mapping", key="close_jm", use_container_width=True
            ):
                st.session_state.job_mapping = None
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════════════════════
def _page_home():
    st.header("Build Industry-Ready Curricula with AI")
    st.write(
        "**CurricuForge** generates complete, semester-wise syllabus in seconds — powered by **Llama 3.3 70B** via Groq + OpenRouter."
    )

    status = get_backend_status()
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        with st.container(border=True):
            st.markdown(
                f"{'🟢' if status['groq_available'] else '🔴'} **Groq**"
            )
            st.caption(
                f"{status['groq_keys']} key{'s' if status['groq_keys'] != 1 else ''}"
                if status["groq_available"]
                else "No key"
            )
    with s2:
        with st.container(border=True):
            st.markdown(
                f"{'🟢' if status['openrouter_available'] else '🟡'} **OpenRouter**"
            )
            st.caption(
                "Fallback ready"
                if status["openrouter_available"]
                else "Optional"
            )
    with s3:
        with st.container(border=True):
            st.markdown("📦 **Exports**")
            st.caption("PDF · JSON · Chat")
    with s4:
        with st.container(border=True):
            st.markdown("⚡ **Speed**")
            st.caption("10–30 seconds")

    st.divider()
    st.subheader("⚙️ How It Works")
    w1, w2, w3, w4 = st.columns(4)
    for col, title, desc in [
        (w1, "Step 1 · Configure", "Enter skill, level, semesters, industry."),
        (w2, "Step 2 · Generate", "AI builds curriculum via Groq/OpenRouter."),
        (w3, "Step 3 · Analyze", "View analytics, job mapping, study plan."),
        (w4, "Step 4 · Export", "PDF, JSON, share, or save to history."),
    ]:
        with col:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(desc)

    st.divider()
    st.subheader("🎯 Choose Your Path")
    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            st.subheader("🎓 Freshers")
            st.write(
                "**Strong academic foundation** with progressive difficulty."
            )
            st.markdown(
                "- ✓ Foundation courses first\n- ✓ Progressive difficulty\n- ✓ BTech / Diploma\n- ✓ 4–8 semesters"
            )
            if st.button(
                "🎓  Start as Fresher",
                key="btn_fresher",
                use_container_width=True,
            ):
                st.session_state.update(
                    current_page="Generator",
                    p_type="fresher",
                    p_level="BTech",
                    p_semesters=4,
                    p_hours=20,
                )
                st.rerun()
    with col2:
        with st.container(border=True):
            st.subheader("💼 Working Professionals")
            st.write("**Less theory**, more industry-focused & hands-on.")
            st.markdown(
                "- ✓ Industry-specific\n- ✓ Hands-on projects\n- ✓ Certifications & Master's\n- ✓ 2–3 semesters"
            )
            if st.button(
                "💼  Start as Professional",
                key="btn_pro",
                use_container_width=True,
            ):
                st.session_state.update(
                    current_page="Generator",
                    p_type="professional",
                    p_level="Professional Certification",
                    p_semesters=2,
                    p_hours=15,
                )
                st.rerun()

    st.divider()
    st.subheader("✨ Platform Features")
    f1, f2, f3, f4 = st.columns(4)
    for col, icon, title, desc in [
        (f1, "📊", "Analytics Dashboard", "Visual charts & insights"),
        (f2, "📅", "AI Study Planner", "Weekly study schedules"),
        (f3, "💼", "Job Role Mapping", "Courses → career paths"),
        (f4, "🎯", "Skill Gap Analysis", "Find what you need to learn"),
    ]:
        with col:
            with st.container(border=True):
                st.markdown(f"{icon} **{title}**")
                st.caption(desc)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
def _page_generator():
    if not AI_ENGINE_AVAILABLE:
        st.error("**ai_engine.py not found.**")
        return

    status = get_backend_status()
    if not status["any_available"]:
        st.error("❌ **No API keys.** Paste keys in `.env` file.")
        st.code(
            "GROQ_API_KEY=gsk_your_key\nOPENROUTER_API_KEY=sk-or-your_key",
            language="bash",
        )
        return

    badges = []
    if status["groq_available"]:
        badges.append(
            f"🟢 Groq ({status['groq_keys']} key{'s' if status['groq_keys'] > 1 else ''})"
        )
    if status["openrouter_available"]:
        badges.append("🟢 OpenRouter")
    st.caption(f"Active: {' · '.join(badges)}")

    pt = st.session_state.get("p_type")
    if pt == "fresher":
        st.info("🎓 **Fresher Mode**")
    elif pt == "professional":
        st.warning("💼 **Professional Mode**")

    left, right = st.columns([1, 2], gap="large")
    with left:
        st.subheader("Curriculum Parameters")
        skill = st.text_input(
            "Skill / Subject *",
            placeholder="e.g. Machine Learning",
            value=st.session_state.get("p_skill", ""),
        )
        _levels = [
            "Diploma",
            "BTech",
            "Master's Degree",
            "Professional Certification",
        ]
        _dlevel = st.session_state.get("p_level", "BTech")
        level = st.selectbox(
            "Education Level *",
            _levels,
            index=_levels.index(_dlevel) if _dlevel in _levels else 1,
        )
        _sopts = [2, 3, 4, 5, 6, 7, 8]
        _dsem = st.session_state.get("p_semesters", 4)
        semesters = st.selectbox(
            "Semesters *",
            _sopts,
            index=_sopts.index(_dsem) if _dsem in _sopts else 2,
            format_func=lambda x: f"{x} Semesters ({x // 2} yr{'s' if x // 2 > 1 else ''})",
        )
        weekly_hours = st.number_input(
            "Weekly Hours",
            min_value=10,
            max_value=40,
            value=st.session_state.get("p_hours", 20),
        )
        industry = st.text_input(
            "Industry Focus",
            placeholder="e.g. AI, FinTech",
            value=st.session_state.get("p_industry", ""),
        )

        # Language selection
        language = st.selectbox(
            "Output Language",
            [
                "English",
                "Hindi",
                "Telugu",
                "Tamil",
                "Kannada",
                "Spanish",
                "French",
                "German",
            ],
            index=0,
            help="Curriculum will be generated in this language",
        )

        # Skill gap toggle
        st.divider()
        skill_gap_mode = st.toggle(
            "🎯 Skill Gap Analysis",
            value=False,
            help="Input your current skills — AI will focus on gaps",
        )
        current_skills = ""
        if skill_gap_mode:
            current_skills = st.text_area(
                "Your current skills",
                placeholder="e.g. Python basics, HTML/CSS, basic SQL...",
                help="List skills you already know. AI will skip basics and focus on what you need to learn.",
            )

        if skill.strip():
            warns = _get_warnings(level, semesters, weekly_hours)
            if warns and not st.session_state.get("dismiss_warnings"):
                for w in warns:
                    st.warning(w)
                if st.button("✕ Dismiss", key="dw"):
                    st.session_state.dismiss_warnings = True
                    st.rerun()

        b1, b2 = st.columns(2)
        with b1:
            clear_clicked = st.button(
                "🗑️ Clear", key="clr", use_container_width=True
            )
        with b2:
            generate_clicked = st.button(
                "Generate ✨", key="gen", use_container_width=True
            )

        if clear_clicked:
            for k, v in _DEFAULTS.items():
                if k not in ("current_page", "chat_history"):
                    st.session_state[k] = v
            st.rerun()

    with right:
        if generate_clicked:
            if not skill.strip():
                st.error("Please enter a skill or subject.")
            else:
                st.session_state.curriculum_result = None
                st.session_state.curriculum_error = None
                st.session_state.study_plan = None
                st.session_state.job_mapping = None
                hint = ""
                if pt == "fresher":
                    hint = " Emphasise strong academic foundation — fundamentals first, progressive difficulty."
                elif pt == "professional":
                    hint = " For working professionals — minimal theory, industry-applicable skills, hands-on from start."

                if skill_gap_mode and current_skills.strip():
                    hint += f" IMPORTANT: The student already knows these skills: {current_skills.strip()}. SKIP basics they already know. Focus the curriculum on GAPS and advanced topics they need to learn."

                if language != "English":
                    hint += f" Generate the entire curriculum (titles, descriptions, topics) in {language} language."

                payload = {
                    "skill": skill.strip() + hint,
                    "level": level,
                    "semesters": semesters,
                    "weekly_hours": weekly_hours,
                    "industry": industry.strip() or skill.strip(),
                }

                with st.status(
                    "Generating curriculum...", expanded=True
                ) as status_widget:
                    st.write("📝 Building prompt...")
                    time.sleep(0.2)
                    be = get_backend_status()
                    st.write(
                        f"🚀 Sending to {'Groq' if be['groq_available'] else 'OpenRouter'} (Llama 3.3 70B)..."
                    )
                    if skill_gap_mode:
                        st.write("🎯 Skill gap analysis enabled...")
                    if language != "English":
                        st.write(f"🌐 Generating in {language}...")
                    st.write("⏳ 10–30 seconds...")
                    try:
                        result = generate_curriculum(payload)
                        if result.get("success"):
                            backend = result.get("backend", "AI")
                            st.write(f"✅ **Generated via {backend}**")
                            st.session_state.curriculum_result = result[
                                "curriculum"
                            ]
                            _save_to_history(result["curriculum"])
                            status_widget.update(
                                label=f"✅ Ready — via {backend}",
                                state="complete",
                                expanded=False,
                            )
                        else:
                            st.session_state.curriculum_error = result.get(
                                "error", "Unknown error."
                            )
                            status_widget.update(
                                label="❌ Failed", state="error", expanded=True
                            )
                    except Exception as exc:
                        st.session_state.curriculum_error = str(exc)
                        status_widget.update(
                            label="❌ Error", state="error", expanded=True
                        )
                st.rerun()

        if st.session_state.curriculum_result:
            _render_curriculum(st.session_state.curriculum_result)
        elif st.session_state.curriculum_error:
            st.error(f"**Failed.** {st.session_state.curriculum_error}")
        else:
            st.info(
                "🚀 **Build Your Vision**\n\nCreate industry-aligned curricula in seconds.\n\n✓ AI-Powered  ·  ✓ Multi-language  ·  ✓ Skill Gap Analysis  ·  ✓ Job Mapping"
            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
def _page_analytics():
    cur = st.session_state.get("curriculum_result")
    if not cur:
        st.info(
            "📊 **Generate a curriculum first** to see analytics.\n\nGo to the **Generator** tab to create one."
        )
        return

    st.header("📊 Curriculum Analytics")
    st.write(f"Analysis of: **{cur.get('curriculum_title','')}**")
    st.divider()

    stats = _compute_analytics(cur)

    # KPIs
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Semesters", len(stats["sem_names"]))
    k2.metric("Total Courses", stats["total_courses"])
    k3.metric("Total Credits", stats["total_credits"])
    k4.metric("Total Topics", stats["total_topics"])
    k5.metric(
        "Topics / Course",
        f"{float(stats['total_topics']) / max(stats['total_courses'], 1):.1f}"
    )

    st.divider()

    # Charts row 1
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 Courses per Semester")
        fig = go.Figure(
            go.Bar(
                x=stats["sem_names"],
                y=stats["sem_courses"],
                marker_color="#6B4EFF",
                text=stats["sem_courses"],
                textposition="auto",
            )
        )
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("📊 Credits per Semester")
        fig = go.Figure(
            go.Bar(
                x=stats["sem_names"],
                y=stats["sem_credits"],
                marker_color="#9B7BFF",
                text=stats["sem_credits"],
                textposition="auto",
            )
        )
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Charts row 2
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("⏰ Weekly Hours per Semester")
        fig = go.Figure(
            go.Scatter(
                x=stats["sem_names"],
                y=stats["sem_hours"],
                mode="lines+markers+text",
                text=stats["sem_hours"],
                textposition="top center",
                line={"color": "#6B4EFF", "width": 3},
                marker={"size": 10, "color": "#6B4EFF"},
            )
        )
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.subheader("🎯 Credit Distribution")
        fig = go.Figure(
            go.Pie(
                labels=stats["sem_names"],
                values=stats["sem_credits"],
                hole=0.4,
                marker_colors=px.colors.sequential.Purples_r,
            )
        )
        fig.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # Difficulty curve
    st.divider()
    st.subheader("📈 Curriculum Difficulty Progression")
    st.write(
        "Based on credit load and course hours — higher values suggest more demanding semesters."
    )
    difficulty = [
        c + h * 0.5 for c, h in zip(stats["sem_credits"], stats["sem_hours"])
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=stats["sem_names"],
            y=difficulty,
            fill="tozeroy",
            mode="lines+markers",
            line={"color": "#6B4EFF", "width": 3},
            marker={"size": 10},
            fillcolor="rgba(107,78,255,0.1)",
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="Difficulty Score",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Topic cloud
    st.divider()
    st.subheader("🏷️ All Topics Covered")
    if stats["all_topics"]:
        st.write(" · ".join(f"**{t}**" for t in stats["all_topics"][:60]))
        if len(stats["all_topics"]) > 60:
            st.caption(f"...and {len(stats['all_topics']) - 60} more topics")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HISTORY
# ══════════════════════════════════════════════════════════════════════════════
def _page_history():
    st.header("🗂️ Curriculum History")
    st.write("All your previously generated curricula, saved automatically.")
    st.divider()

    items = _load_history()
    if not items:
        st.info(
            "📭 **No saved curricula yet.** Generate one in the **Generator** tab — it auto-saves!"
        )
        return

    st.caption(f"{len(items)} saved curricula")

    for i, item in enumerate(items):
        cur = item.get("curriculum", {})
        title = cur.get("curriculum_title", "Untitled")
        saved_at = item.get("saved_at", "")
        level = cur.get("level", "")
        sems = len(cur.get("semesters", []))
        courses = sum(
            len(s.get("courses", [])) for s in cur.get("semesters", [])
        )

        with st.container(border=True):
            h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
            with h1:
                st.markdown(f"**{title}**")
                st.caption(
                    f"🎓 {level}  ·  📅 {sems} semesters  ·  📚 {courses} courses  ·  🕐 {saved_at[:16]}"
                )
            with h2:
                if st.button(
                    "📂 Load", key=f"load_{i}", use_container_width=True
                ):
                    st.session_state.curriculum_result = cur
                    st.session_state.current_page = "Generator"
                    st.rerun()
            with h3:
                if st.button(
                    "📊 Analyze", key=f"analyze_{i}", use_container_width=True
                ):
                    st.session_state.curriculum_result = cur
                    st.session_state.current_page = "Analytics"
                    st.rerun()
            with h4:
                if st.button("🗑️", key=f"del_{i}", use_container_width=True):
                    _delete_history_item(item.get("_filename", ""))
                    st.rerun()

    st.divider()
    if st.button("🗑️ Clear All History", key="clear_all_hist"):
        for item in items:
            _delete_history_item(item.get("_filename", ""))
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: COMPARE
# ══════════════════════════════════════════════════════════════════════════════
def _page_compare():
    st.header("🔄 Compare Curricula")
    st.write(
        "Generate two curricula for different skills and compare them side-by-side."
    )
    st.divider()

    items = _load_history()
    if len(items) < 2:
        st.info(
            "📭 **Need at least 2 saved curricula.** Generate curricula in the **Generator** tab — they auto-save!"
        )
        return

    titles = [
        item.get("curriculum", {}).get("curriculum_title", "Untitled")
        for item in items
    ]

    c1, c2 = st.columns(2)
    with c1:
        idx1 = st.selectbox(
            "Curriculum A",
            range(len(titles)),
            format_func=lambda i: titles[i],
            key="cmp_a",
        )
    with c2:
        idx2 = st.selectbox(
            "Curriculum B",
            range(len(titles)),
            format_func=lambda i: titles[i],
            index=min(1, len(titles) - 1),
            key="cmp_b",
        )

    if idx1 == idx2:
        st.warning("Select two different curricula to compare.")
        return

    cur_a = items[idx1]["curriculum"]
    cur_b = items[idx2]["curriculum"]
    stats_a = _compute_analytics(cur_a)
    stats_b = _compute_analytics(cur_b)

    st.divider()

    # Comparison KPIs
    st.subheader("📊 Quick Comparison")
    metrics = [
        ("Semesters", len(stats_a["sem_names"]), len(stats_b["sem_names"])),
        ("Courses", stats_a["total_courses"], stats_b["total_courses"]),
        ("Credits", stats_a["total_credits"], stats_b["total_credits"]),
        ("Topics", stats_a["total_topics"], stats_b["total_topics"]),
    ]

    cols = st.columns(len(metrics))
    for col, (label, va, vb) in zip(cols, metrics):
        with col:
            with st.container(border=True):
                st.markdown(f"**{label}**")
                st.write(f"A: **{va}**  vs  B: **{vb}**")
                diff = va - vb
                if diff > 0:
                    st.caption(f"A has {diff} more")
                elif diff < 0:
                    st.caption(f"B has {abs(diff)} more")
                else:
                    st.caption("Equal")

    # Side-by-side charts
    st.divider()
    st.subheader("📈 Credits per Semester")
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=stats_a["sem_names"],
            y=stats_a["sem_credits"],
            name=titles[idx1][:20],
            marker_color="#6B4EFF",
        )
    )
    fig.add_trace(
        go.Bar(
            x=stats_b["sem_names"],
            y=stats_b["sem_credits"],
            name=titles[idx2][:20],
            marker_color="#FF6B4E",
        )
    )
    fig.update_layout(
        barmode="group",
        height=350,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Side-by-side curricula
    st.divider()
    st.subheader("📋 Side-by-Side View")
    left, right = st.columns(2)
    with left:
        st.markdown(f"### A: {cur_a.get('curriculum_title','')}")
        for sem in cur_a.get("semesters", []):
            with st.expander(f"Sem {sem.get('semester_number','')}"):
                for c in sem.get("courses", []):
                    st.write(
                        f"• **{c.get('course_name','')}** ({c.get('credits',4)} cr)"
                    )
    with right:
        st.markdown(f"### B: {cur_b.get('curriculum_title','')}")
        for sem in cur_b.get("semesters", []):
            with st.expander(f"Sem {sem.get('semester_number','')}"):
                for c in sem.get("courses", []):
                    st.write(
                        f"• **{c.get('course_name','')}** ({c.get('credits',4)} cr)"
                    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CHAT
# ══════════════════════════════════════════════════════════════════════════════
def _page_chat():
    ctx = st.session_state.get("curriculum_chat_context")

    if ctx:
        st.header("💬 Ask Doubts — Curriculum Q&A")
        st.write(
            f"Asking about: **{ctx.get('curriculum_title', 'your curriculum')}**"
        )
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button(
                "🗑️ Clear", key="clear_chat", use_container_width=True
            ):
                st.session_state.chat_history = []
                st.rerun()
        with c2:
            if st.button(
                "↩️ Exit Doubts", key="exit_doubts", use_container_width=True
            ):
                st.session_state.curriculum_chat_context = None
                st.session_state.chat_history = []
                st.rerun()
    else:
        st.header("💬 CurricuForge Assistant")
        st.write(
            "Ask about **curriculum design, education, course planning, skill development**, or learning paths."
        )
        col_clear, _ = st.columns([1, 5])
        with col_clear:
            if st.button(
                "🗑️ Clear Chat", key="clear_chat", use_container_width=True
            ):
                st.session_state.chat_history = []
                st.rerun()

    st.divider()
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if not st.session_state.chat_history:
        with st.chat_message("assistant"):
            if ctx:
                title = ctx.get("curriculum_title", "")
                st.write(
                    f"👋 I have your **{title}** loaded. Ask me anything!"
                )
            else:
                st.write(
                    "👋 Hello! I can help with curriculum design, career paths, and skill development."
                )

    chat_placeholder = (
        "Ask about your curriculum..." if ctx else "Ask a question..."
    )
    user_input = st.chat_input(chat_placeholder)
    if user_input:
        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )
        with st.chat_message("user"):
            st.write(user_input)

        extra_history = list(st.session_state.chat_history[:-1])
        if ctx and not extra_history:
            summary = _build_curriculum_summary(ctx)
            extra_history.insert(
                0,
                {
                    "role": "user",
                    "content": f"Here is my curriculum:\n\n{summary}\n\nAnswer questions about it.",
                },
            )
            extra_history.insert(
                1,
                {
                    "role": "assistant",
                    "content": "I've reviewed the curriculum. Ask me anything!",
                },
            )

        with st.chat_message("assistant"):
            with st.status("Thinking...", expanded=True) as status_widget:
                st.write("🤖 Consulting AI...")
                if AI_ENGINE_AVAILABLE:
                    response, backend = chat_with_llm(
                        user_input, extra_history, CHAT_SYSTEM_PROMPT
                    )
                else:
                    response, backend = "❌ ai_engine.py not found.", "none"
                status_widget.update(
                    label="✅ Ready", state="complete", expanded=False
                )
            st.write(response)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": response}
        )
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ABOUT
# ══════════════════════════════════════════════════════════════════════════════
def _page_about():
    st.header("About CurricuForge")
    st.write(
        "AI-powered platform for structured, "
        "semester-wise curriculum generation."
    )
    st.divider()

    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            st.subheader("🧠 AI Architecture")
            st.write(
                "**Primary:** Groq (Llama 3.3 70B) "
                "with round-robin key rotation."
            )
            st.write(
                "**Fallback:** OpenRouter — "
                "auto-switches when Groq is unavailable."
            )
            status = get_backend_status()
            st.markdown(
                f"{'🟢' if status['groq_available'] else '🔴'} "
                f"Groq ({status['groq_keys']} keys)  ·  "
                f"{'🟢' if status['openrouter_available'] else '🔴'} "
                f"OpenRouter"
            )

        with st.container(border=True):
            st.subheader("🎯 Who Is This For?")
            st.markdown(
                "- **Educators** — Design/update syllabi\n"
                "- **Institutions** — Rapid prototyping\n"
                "- **Companies** — Upskilling programs\n"
                "- **Students** — Learning paths"
            )

    with c2:
        with st.container(border=True):
            st.subheader("🛠️ Tech Stack")
            st.markdown(
                "- **Frontend:** Streamlit\n"
                "- **AI:** Groq + OpenRouter (Llama 3.3 70B)\n"
                "- **Charts:** Plotly\n"
                "- **PDF:** ReportLab\n"
                "- **Language:** Python 3.x"
            )

        with st.container(border=True):
            st.subheader("⚡ Features")
            st.markdown(
                "- ✓ Multi-backend AI + key rotation\n"
                "- ✓ Skill gap analysis\n"
                "- ✓ Multi-language support\n"
                "- ✓ Analytics dashboard (Plotly)\n"
                "- ✓ Curriculum history & comparison\n"
                "- ✓ AI study planner\n"
                "- ✓ Job role mapping\n"
                "- ✓ AI chatbot for doubts\n"
                "- ✓ PDF & JSON exports\n"
                "- ✓ Fresher / Professional modes"
            )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    st.title("🎓 CurricuForge")
    st.caption("AI-Powered Curriculum Generation · Groq + OpenRouter")

    _pages = [
        "Home",
        "Generator",
        "Analytics",
        "History",
        "Compare",
        "Chat",
        "About",
    ]
    current = st.session_state.get("current_page", "Home")
    if current not in _pages:
        current = "Home"

    page = st.radio(
        "Navigate",
        [
            "🏠 Home",
            "⚒️ Generator",
            "📊 Analytics",
            "🗂️ History",
            "🔄 Compare",
            "💬 Chat",
            "ℹ️ About",
        ],
        index=_pages.index(current),
        horizontal=True,
        label_visibility="collapsed",
    )

    _map = {
        "🏠 Home": "Home",
        "⚒️ Generator": "Generator",
        "📊 Analytics": "Analytics",
        "🗂️ History": "History",
        "🔄 Compare": "Compare",
        "💬 Chat": "Chat",
        "ℹ️ About": "About",
    }
    selected = _map.get(page, "Home")

    if selected != st.session_state.get("current_page"):
        st.session_state.current_page = selected
        st.rerun()

    st.divider()

    pages_dict = {
        "Home": _page_home,
        "Generator": _page_generator,
        "Analytics": _page_analytics,
        "History": _page_history,
        "Compare": _page_compare,
        "Chat": _page_chat,
        "About": _page_about,
    }
    pages_dict[selected]()


if __name__ == "__main__":
    main()
