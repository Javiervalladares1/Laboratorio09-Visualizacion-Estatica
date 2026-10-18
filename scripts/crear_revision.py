"""Exporta a PDF la nota Markdown de revisión técnica, sin alterar el avance."""
from functools import partial
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, KeepTogether, PageBreak

ROOT = Path(__file__).resolve().parents[1]
STEM = ROOT / 'documento' / 'Revision_y_Mejoras_2026-10-19'


def main():
    styles = {
        'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=21,
                                leading=25, textColor=colors.HexColor('#16324F'), spaceAfter=14),
        'heading': ParagraphStyle('heading', fontName='Helvetica-Bold', fontSize=13,
                                  leading=17, spaceBefore=12, spaceAfter=7,
                                  textColor=colors.HexColor('#006D77'), keepWithNext=True),
        'body': ParagraphStyle('body', fontName='Helvetica', fontSize=10.3,
                               leading=14.2, spaceAfter=8, textColor=colors.HexColor('#182A36')),
        'bullet': ParagraphStyle('bullet', fontName='Helvetica', fontSize=10.3,
                                 leading=14.2, leftIndent=10, firstLineIndent=-10,
                                 spaceAfter=7, textColor=colors.HexColor('#182A36')),
    }
    story = []
    for block in STEM.with_suffix('.md').read_text(encoding='utf-8').strip().split('\n\n'):
        if block.startswith('# '):
            story.append(Paragraph(escape(block[2:]), styles['title']))
        elif block.startswith('## '):
            if block == '## Correspondencia con la guía':
                story.append(PageBreak())
            story.append(Paragraph(escape(block[3:]), styles['heading']))
        elif block.startswith('- '):
            items = []
            for line in block.splitlines():
                items.append(Paragraph('- ' + escape(line.removeprefix('- ')), styles['bullet']))
            story.append(KeepTogether(items))
        else:
            story.append(Paragraph(escape(block).replace('\n', ' '), styles['body']))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#E0E5E9'))
        canvas.line(43, 37, A4[0] - 43, 37)
        canvas.setFillColor(colors.HexColor('#525866'))
        canvas.setFont('Helvetica', 8)
        canvas.drawString(43, 24, 'Laboratorio 09 | Revisión del 19 de octubre de 2026')
        canvas.drawRightString(A4[0] - 43, 24, str(doc.page))
        canvas.restoreState()

    document = SimpleDocTemplate(str(STEM.with_suffix('.pdf')), pagesize=A4,
                                 leftMargin=43, rightMargin=43, topMargin=43, bottomMargin=53,
                                 title='Revisión técnica y visual del Laboratorio 09',
                                 author='Revisión con asistencia de Codex')
    document.build(story, onFirstPage=footer, onLaterPages=footer,
                   canvasmaker=partial(Canvas, invariant=1))
    print(STEM.with_suffix('.pdf'))


if __name__ == '__main__':
    main()
