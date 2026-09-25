"""Generate original synthetic study material; never use this as real eval evidence."""

import sys
from pathlib import Path

from reportlab.pdfgen import canvas

output = Path(sys.argv[1] if len(sys.argv) > 1 else "tmp/demo-physics.pdf")
output.parent.mkdir(parents=True, exist_ok=True)
pdf = canvas.Canvas(str(output), invariant=True)
pdf.setTitle("Physics - generated demo")
for title, text in [
    ("01 / Gravity", "Gravity is an attractive force between objects with mass."),
    ("02 / Inertia", "Inertia is the tendency of an object to resist changes in motion."),
]:
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(50, 750, title)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 700, text)
    pdf.showPage()
pdf.save()
print(output)
