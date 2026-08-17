from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


NAVY = HexColor("#1e3a5f")
GOLD = HexColor("#c9a227")
CREAM = HexColor("#fbf7ef")
GRAY = HexColor("#475569")


def fit_size(c, text, font, size, max_width):
    while size > 11 and c.stringWidth(text, font, size) > max_width:
        size -= 1
    return size


def draw_certificate(c, enrollment, page_w, page_h):
    name = enrollment.employee.get_full_name().strip()
    if not name:
        name = enrollment.employee.email
    course = enrollment.course.title
    if enrollment.quiz_taken_at:
        date_text = enrollment.quiz_taken_at.strftime("%B %d, %Y")
    else:
        date_text = ""

    c.setFillColor(CREAM)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    c.setStrokeColor(NAVY)
    c.setLineWidth(16)
    c.rect(16, 16, page_w - 32, page_h - 32, fill=0, stroke=1)

    c.setStrokeColor(GOLD)
    c.setLineWidth(3)
    c.rect(28, 28, page_w - 56, page_h - 56, fill=0, stroke=1)

    c.setStrokeColor(NAVY)
    c.setLineWidth(1)
    c.rect(36, 36, page_w - 72, page_h - 72, fill=0, stroke=1)

    cx = page_w / 2
    max_w = page_w - 140

    c.setFillColor(GOLD)
    c.setFont("Times-Bold", 12)
    c.drawCentredString(cx, page_h - 88, "LMS")

    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 28)
    c.drawCentredString(cx, page_h - 128, "CERTIFICATE OF COMPLETION")

    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(cx - 120, page_h - 142, cx + 120, page_h - 142)

    c.setFillColor(GRAY)
    c.setFont("Times-Italic", 14)
    c.drawCentredString(cx, page_h - 178, "This is to certify that")

    name_size = fit_size(c, name, "Times-BoldItalic", 30, max_w)
    c.setFillColor(NAVY)
    c.setFont("Times-BoldItalic", name_size)
    c.drawCentredString(cx, page_h - 230, name)

    c.setStrokeColor(GOLD)
    c.line(cx - 200, page_h - 242, cx + 200, page_h - 242)

    c.setFillColor(GRAY)
    c.setFont("Times-Italic", 14)
    c.drawCentredString(cx, page_h - 280, "has successfully completed the course")

    course_size = fit_size(c, course, "Times-Bold", 20, max_w)
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", course_size)
    c.drawCentredString(cx, page_h - 322, course)

    c.setStrokeColor(NAVY)
    c.setLineWidth(1)
    c.line(90, 88, 250, 88)
    c.line(page_w - 250, 88, page_w - 90, 88)

    c.setFillColor(GRAY)
    c.setFont("Times-Roman", 10)
    c.drawCentredString(170, 70, date_text)
    c.drawCentredString(170, 56, "DATE")
    c.drawCentredString(page_w - 170, 70, "LMS")
    c.drawCentredString(page_w - 170, 56, "AUTHORIZED")

    c.setFillColor(GOLD)
    c.circle(cx, 92, 40, fill=1, stroke=0)
    c.setStrokeColor(NAVY)
    c.setLineWidth(2)
    c.circle(cx, 92, 40, fill=0, stroke=1)
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 11)
    c.drawCentredString(cx, 96, "LMS")
    c.drawCentredString(cx, 80, "SEAL")


def build_certificate_pdf(enrollment):
    buffer = BytesIO()
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    draw_certificate(c, enrollment, page_w, page_h)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
