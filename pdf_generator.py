"""
CurricuForge — PDF Generator
Takes curriculum JSON from ai_engine.py and generates
a professional formatted PDF syllabus using ReportLab.
Supports Unicode (Telugu, Hindi, Tamil, etc.) via Arial Unicode MS.
"""

import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ─────────────────────────────────────────
# UNICODE FONT REGISTRATION
# ─────────────────────────────────────────
_UNICODE_FONT = "Helvetica"
_UNICODE_FONT_BOLD = "Helvetica-Bold"

_FONT_PATHS = [
    # macOS
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    # Linux / Streamlit Cloud (from packages.txt: fonts-noto)
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

for _path in _FONT_PATHS:
    if os.path.exists(_path):
        try:
            pdfmetrics.registerFont(TTFont("ArialUnicode", _path))
            _UNICODE_FONT = "ArialUnicode"
            _UNICODE_FONT_BOLD = "ArialUnicode"  # TTF has no separate bold file
            print(f"[PDF] Registered Unicode font: {_path}")
            break
        except Exception as e:
            print(f"[PDF] Failed to register {_path}: {e}")
else:
    print("[PDF] No Unicode font found — non-Latin scripts may not render in PDF")



# ─────────────────────────────────────────
# COLORS — CurricuForge Brand
# ─────────────────────────────────────────
PRIMARY     = colors.HexColor("#1A1A2E")   # Dark navy
SECONDARY   = colors.HexColor("#16213E")   # Slightly lighter navy
ACCENT      = colors.HexColor("#0F3460")   # Blue
HIGHLIGHT   = colors.HexColor("#E94560")   # Red accent
LIGHT_BG    = colors.HexColor("#F5F5F5")   # Light grey background
WHITE       = colors.white
TEXT_DARK   = colors.HexColor("#2C2C2C")   # Near black text
TEXT_LIGHT  = colors.HexColor("#666666")   # Grey text
TAG_BG      = colors.HexColor("#E8F4FD")   # Light blue for topic tags
TAG_BORDER  = colors.HexColor("#2196F3")   # Blue border for tags


# ─────────────────────────────────────────
# STYLES SETUP
# ─────────────────────────────────────────

def build_styles():
    """Creates all custom paragraph styles used in the PDF."""
    base = getSampleStyleSheet()

    styles = {

        # Cover page — main title
        "cover_title": ParagraphStyle(
            "cover_title",
            fontSize=28,
            fontName=_UNICODE_FONT_BOLD,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=8,
            leading=34
        ),

        # Cover page — subtitle
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            fontSize=14,
            fontName=_UNICODE_FONT,
            textColor=colors.HexColor("#CCCCCC"),
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=18
        ),

        # Cover page — meta info
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontSize=11,
            fontName=_UNICODE_FONT,
            textColor=colors.HexColor("#AAAAAA"),
            alignment=TA_CENTER,
            spaceAfter=4,
        ),

        # Section headers (e.g. SEMESTER 1)
        "semester_header": ParagraphStyle(
            "semester_header",
            fontSize=13,
            fontName=_UNICODE_FONT_BOLD,
            textColor=WHITE,
            alignment=TA_LEFT,
            spaceAfter=0,
            spaceBefore=16,
            leading=18
        ),

        # Course name inside table
        "course_name": ParagraphStyle(
            "course_name",
            fontSize=11,
            fontName=_UNICODE_FONT_BOLD,
            textColor=PRIMARY,
            spaceAfter=2,
            leading=14
        ),

        # Course code badge
        "course_code": ParagraphStyle(
            "course_code",
            fontSize=9,
            fontName=_UNICODE_FONT_BOLD,
            textColor=HIGHLIGHT,
            spaceAfter=2,
        ),

        # Course description
        "course_desc": ParagraphStyle(
            "course_desc",
            fontSize=9,
            fontName=_UNICODE_FONT,
            textColor=TEXT_DARK,
            spaceAfter=4,
            leading=13,
            alignment=TA_JUSTIFY
        ),

        # Topic tags
        "topic_tag": ParagraphStyle(
            "topic_tag",
            fontSize=8,
            fontName=_UNICODE_FONT,
            textColor=colors.HexColor("#1565C0"),
            spaceAfter=2,
        ),

        # Table header text
        "table_header": ParagraphStyle(
            "table_header",
            fontSize=9,
            fontName=_UNICODE_FONT_BOLD,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),

        # Table cell text
        "table_cell": ParagraphStyle(
            "table_cell",
            fontSize=9,
            fontName=_UNICODE_FONT,
            textColor=TEXT_DARK,
            alignment=TA_CENTER,
        ),

        # Capstone section title
        "capstone_title": ParagraphStyle(
            "capstone_title",
            fontSize=14,
            fontName=_UNICODE_FONT_BOLD,
            textColor=PRIMARY,
            spaceAfter=6,
            spaceBefore=8,
        ),

        # Capstone description
        "capstone_desc": ParagraphStyle(
            "capstone_desc",
            fontSize=10,
            fontName=_UNICODE_FONT,
            textColor=TEXT_DARK,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),

        # Section label (small uppercase)
        "section_label": ParagraphStyle(
            "section_label",
            fontSize=8,
            fontName=_UNICODE_FONT_BOLD,
            textColor=TEXT_LIGHT,
            spaceAfter=4,
            spaceBefore=8,
        ),
    }

    return styles


# ─────────────────────────────────────────
# COVER PAGE BUILDER
# ─────────────────────────────────────────

def build_cover_page(curriculum: dict, styles: dict) -> list:
    """Builds the cover page elements."""
    story = []

    title_text = curriculum.get("curriculum_title", "Curriculum Syllabus")
    level       = curriculum.get("level", "")
    skill       = curriculum.get("skill_domain", "")
    industry    = curriculum.get("industry_focus", "")
    semesters   = curriculum.get("total_semesters", "")
    hours       = curriculum.get("weekly_hours", "")
    total_courses = sum(len(s.get("courses", [])) for s in curriculum.get("semesters", []))
    total_topics  = sum(len(c.get("topics", [])) for s in curriculum.get("semesters", []) for c in s.get("courses", []))

    # Cover block
    cover_data = [[
        Paragraph("<br/>", styles["cover_meta"]),
    ], [
        Paragraph("CurricuForge", styles["cover_subtitle"]),
    ], [
        Paragraph(title_text, styles["cover_title"]),
    ], [
        Paragraph(f"{level} &nbsp;|&nbsp; {skill} &nbsp;|&nbsp; {industry}", styles["cover_subtitle"]),
    ], [
        Paragraph(f"<br/>Semesters: {semesters} &nbsp;&nbsp; Weekly Hours: {hours} &nbsp;&nbsp; Courses: {total_courses} &nbsp;&nbsp; Topics: {total_topics}", styles["cover_meta"]),
    ], [
        Paragraph("<br/>", styles["cover_meta"]),
    ]]

    cover_table = Table(cover_data, colWidths=[170 * mm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), PRIMARY),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
    ]))

    story.append(cover_table)
    story.append(Spacer(1, 6 * mm))

    # Summary stats bar
    stats_data = [[
        Paragraph("LEVEL", styles["section_label"]),
        Paragraph("DOMAIN", styles["section_label"]),
        Paragraph("INDUSTRY", styles["section_label"]),
        Paragraph("SEMESTERS", styles["section_label"]),
        Paragraph("HRS/WEEK", styles["section_label"]),
    ], [
        Paragraph(f"<b>{level}</b>", styles["course_name"]),
        Paragraph(f"<b>{skill}</b>", styles["course_name"]),
        Paragraph(f"<b>{industry}</b>", styles["course_name"]),
        Paragraph(f"<b>{semesters}</b>", styles["course_name"]),
        Paragraph(f"<b>{hours}</b>", styles["course_name"]),
    ]]

    stats_table = Table(stats_data, colWidths=[34 * mm] * 5)
    stats_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BG),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, 0), 0.5, colors.HexColor("#DDDDDD")),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
    ]))

    story.append(stats_table)
    story.append(Spacer(1, 4 * mm))

    # Start first semester on same page (no PageBreak)
    return story


# ─────────────────────────────────────────
# SEMESTER SECTION BUILDER
# ─────────────────────────────────────────

def build_semester_section(semester: dict, styles: dict) -> list:
    """Builds one full semester section with all its courses."""
    story = []

    sem_num   = semester.get("semester_number", "")
    sem_title = semester.get("semester_title", f"Semester {sem_num}")
    courses   = semester.get("courses", [])

    # Semester header bar
    header_data = [[
        Paragraph(f"SEMESTER {sem_num} — {sem_title.upper()}", styles["semester_header"])
    ]]
    header_table = Table(header_data, colWidths=[170 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), ACCENT),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 3 * mm))

    # Course summary table header
    summary_header = [[
        Paragraph("CODE",        styles["table_header"]),
        Paragraph("COURSE NAME", styles["table_header"]),
        Paragraph("CREDITS",     styles["table_header"]),
        Paragraph("HRS/WEEK",    styles["table_header"]),
    ]]

    summary_rows = []
    for course in courses:
        summary_rows.append([
            Paragraph(course.get("course_code", ""), styles["table_cell"]),
            Paragraph(course.get("course_name", ""), styles["table_cell"]),
            Paragraph(str(course.get("credits", 4)),        styles["table_cell"]),
            Paragraph(str(course.get("hours_per_week", 3)), styles["table_cell"]),
        ])

    summary_data  = summary_header + summary_rows
    summary_table = Table(
        summary_data,
        colWidths=[22 * mm, 100 * mm, 24 * mm, 24 * mm]
    )

    # Alternating row colors
    row_styles = [
        ("BACKGROUND",    (0, 0), (-1, 0),  PRIMARY),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.HexColor("#EEEEEE")),
    ]
    for i in range(1, len(summary_data)):
        bg = LIGHT_BG if i % 2 == 0 else WHITE
        row_styles.append(("BACKGROUND", (0, i), (-1, i), bg))

    summary_table.setStyle(TableStyle(row_styles))
    story.append(summary_table)
    story.append(Spacer(1, 5 * mm))

    # Individual course detail cards
    for course in courses:
        story.extend(build_course_card(course, styles))

    return story


# ─────────────────────────────────────────
# COURSE CARD BUILDER
# ─────────────────────────────────────────

def build_course_card(course: dict, styles: dict) -> list:
    """Builds a detailed card for a single course."""
    story = []

    code        = course.get("course_code", "")
    name        = course.get("course_name", "")
    description = course.get("description", "")
    topics      = course.get("topics", [])
    credits     = course.get("credits", 4)
    hours       = course.get("hours_per_week", 3)

    # Topics as inline tags
    topic_tags = "  ".join([f"[ {t} ]" for t in topics])

    card_content = [
        [
            Paragraph(f"{code}", styles["course_code"]),
            Paragraph(f"Credits: {credits} &nbsp;&nbsp; Hours/Week: {hours}", styles["topic_tag"]),
        ],
        [
            Paragraph(name, styles["course_name"]),
            Paragraph("", styles["course_name"]),
        ],
        [
            Paragraph(description, styles["course_desc"]),
            Paragraph("", styles["course_desc"]),
        ],
        [
            Paragraph(f"<font color='#1565C0'>{topic_tags}</font>", styles["topic_tag"]),
            Paragraph("", styles["topic_tag"]),
        ],
    ]

    card_table = Table(card_content, colWidths=[130 * mm, 40 * mm])
    card_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), WHITE),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("LINEBELOW",     (0, 0), (-1, 0),  0.5, colors.HexColor("#EEEEEE")),
        ("SPAN",          (0, 1), (1, 1)),
        ("SPAN",          (0, 2), (1, 2)),
        ("SPAN",          (0, 3), (1, 3)),
    ]))

    story.append(card_table)
    story.append(Spacer(1, 2 * mm))

    return story


# ─────────────────────────────────────────
# CAPSTONE SECTION BUILDER
# ─────────────────────────────────────────

def build_capstone_section(capstone: dict, styles: dict) -> list:
    """Builds the capstone project section."""
    story = []

    story.append(PageBreak())

    # Capstone header
    cap_header = [[
        Paragraph("CAPSTONE PROJECT", styles["semester_header"])
    ]]
    cap_table = Table(cap_header, colWidths=[170 * mm])
    cap_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), HIGHLIGHT),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(cap_table)
    story.append(Spacer(1, 5 * mm))

    title = capstone.get("title", "Capstone Project")
    desc  = capstone.get("description", "")

    story.append(Paragraph(title, styles["capstone_title"]))
    story.append(HRFlowable(width="100%", thickness=1, color=HIGHLIGHT))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(desc, styles["capstone_desc"]))

    return story


# ─────────────────────────────────────────
# MAIN PDF GENERATOR FUNCTION
# ─────────────────────────────────────────

def generate_pdf(curriculum: dict) -> bytes:
    """
    MAIN FUNCTION — called by Streamlit app.

    Takes the curriculum dict from ai_engine.py
    and returns PDF as bytes (for Streamlit download button).

    Usage:
        pdf_bytes = generate_pdf(result["curriculum"])
        st.download_button("Download PDF", pdf_bytes, "curriculum.pdf")
    """

    # Build into memory buffer (no file saved to disk)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=curriculum.get("curriculum_title", "CurricuForge Syllabus"),
        author="CurricuForge — Powered by Groq AI"
    )

    styles = build_styles()
    story  = []

    # 1. Cover page
    story.extend(build_cover_page(curriculum, styles))

    # 2. Each semester
    for semester in curriculum.get("semesters", []):
        story.extend(build_semester_section(semester, styles))
        story.append(Spacer(1, 5 * mm))

    # 3. Capstone project
    capstone = curriculum.get("capstone_project")
    if capstone:
        story.extend(build_capstone_section(capstone, styles))

    # Build the PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_text_pdf(title: str, content: str, subtitle: str = "") -> bytes:
    """
    Generate a PDF from a title and text content (for Study Plan, Job Mapping, etc.).
    Returns PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title=title, author="CurricuForge — Powered by Groq AI"
    )

    styles = build_styles()
    story = []

    # Header
    header_data = [[
        Paragraph("CurricuForge", styles["cover_subtitle"]),
    ], [
        Paragraph(title, styles["cover_title"]),
    ]]
    if subtitle:
        header_data.append([Paragraph(subtitle, styles["cover_subtitle"])])
    header_data.append([Paragraph("<br/>", styles["cover_meta"])])

    header_table = Table(header_data, colWidths=[170 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PRIMARY),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))

    # Body text style
    body_style = ParagraphStyle(
        "body_text", fontSize=10, fontName=_UNICODE_FONT,
        textColor=TEXT_DARK, leading=16, alignment=TA_JUSTIFY, spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "content_heading", fontSize=12, fontName=_UNICODE_FONT_BOLD,
        textColor=PRIMARY, spaceBefore=12, spaceAfter=4, leading=16,
    )

    # Parse content — split by lines, detect headings
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2 * mm))
            continue
        # Detect markdown headings
        if line.startswith("### "):
            story.append(Paragraph(line[4:], heading_style))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], heading_style))
        elif line.startswith("# "):
            story.append(Paragraph(line[2:], heading_style))
        elif line.startswith("**") and line.endswith("**"):
            story.append(Paragraph(f"<b>{line.strip('*')}</b>", heading_style))
        elif line.startswith("- ") or line.startswith("• "):
            bullet_text = line[2:].replace("**", "").replace("*", "")
            story.append(Paragraph(f"&bull; {bullet_text}", body_style))
        elif line.startswith("* "):
            bullet_text = line[2:].replace("**", "").replace("*", "")
            story.append(Paragraph(f"&bull; {bullet_text}", body_style))
        else:
            # Clean markdown bold/italic
            clean = line.replace("**", "").replace("*", "")
            story.append(Paragraph(clean, body_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ─────────────────────────────────────────
# QUICK TEST (run directly: python pdf_generator.py)
# ─────────────────────────────────────────

if __name__ == "__main__":
    # Sample curriculum to test with
    sample = {
        "curriculum_title": "BTech in Machine Learning (AI focused)",
        "level": "BTech",
        "skill_domain": "Machine Learning",
        "industry_focus": "AI",
        "total_semesters": 2,
        "weekly_hours": 20,
        "semesters": [
            {
                "semester_number": 1,
                "semester_title": "Fundamentals of Machine Learning",
                "courses": [
                    {
                        "course_code": "CS101",
                        "course_name": "Introduction to Machine Learning",
                        "credits": 4,
                        "hours_per_week": 3,
                        "description": "An introduction to the core concepts of Machine Learning, including supervised, unsupervised, and reinforcement learning.",
                        "topics": ["ML Basics", "Supervised Learning", "Unsupervised Learning", "Reinforcement Learning"]
                    },
                    {
                        "course_code": "CS102",
                        "course_name": "Mathematics for Machine Learning",
                        "credits": 4,
                        "hours_per_week": 3,
                        "description": "Essential mathematical concepts required for understanding and implementing Machine Learning algorithms.",
                        "topics": ["Linear Algebra", "Calculus", "Probability Theory", "Statistical Inference"]
                    }
                ]
            },
            {
                "semester_number": 2,
                "semester_title": "Advanced Machine Learning Techniques",
                "courses": [
                    {
                        "course_code": "CS201",
                        "course_name": "Deep Learning",
                        "credits": 4,
                        "hours_per_week": 3,
                        "description": "A deep dive into neural networks, CNNs, RNNs, and transformer architectures.",
                        "topics": ["Neural Networks", "CNNs", "RNNs", "Transformers", "GANs"]
                    }
                ]
            }
        ],
        "capstone_project": {
            "title": "Capstone Project in Machine Learning",
            "description": "Students will apply all skills learned throughout the program to design, develop, and present a comprehensive real-world ML project evaluated by industry professionals."
        }
    }

    print("Generating PDF...")
    pdf_bytes = generate_pdf(sample)

    with open("test_curriculum.pdf", "wb") as f:
        f.write(pdf_bytes)

    print(f"✅ PDF generated successfully! ({len(pdf_bytes):,} bytes)")
    print("Saved as: test_curriculum.pdf")