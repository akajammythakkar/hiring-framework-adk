"""
PDF Generator for Evaluation Reports
Generates comprehensive PDF reports with all evaluation data
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, Optional
import re


class PDFReportGenerator:
    """Generate PDF reports for candidate evaluations"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _markdown_to_pdf_elements(self, text: str) -> list:
        """
        Convert markdown text to PDF elements (Paragraphs with proper formatting)
        Preserves headings, bold, italic, and bullet points
        """
        if not text:
            return []
        
        elements = []
        lines = text.split('\n')
        i = 0
        current_paragraph = []
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                if current_paragraph:
                    # Flush current paragraph
                    para_text = ' '.join(current_paragraph)
                    elements.append(Paragraph(self._convert_inline_markdown(para_text), self.styles['Normal']))
                    elements.append(Spacer(1, 0.1*inch))
                    current_paragraph = []
                i += 1
                continue
            
            # Handle headers
            if line.startswith('#'):
                # Flush current paragraph first
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    elements.append(Paragraph(self._convert_inline_markdown(para_text), self.styles['Normal']))
                    current_paragraph = []
                
                # Determine header level
                header_match = re.match(r'^(#{1,6})\s+(.+)', line)
                if header_match:
                    level = len(header_match.group(1))
                    header_text = header_match.group(2)
                    
                    # Use appropriate style based on level
                    if level == 1:
                        style = self.styles['Heading1']
                    elif level == 2:
                        style = self.styles['SectionHeader']
                    elif level == 3:
                        style = self.styles['SubSection']
                    else:
                        style = self.styles['Heading4']
                    
                    elements.append(Spacer(1, 0.15*inch))
                    elements.append(Paragraph(self._convert_inline_markdown(header_text), style))
                    elements.append(Spacer(1, 0.1*inch))
                
                i += 1
                continue
            
            # Handle bullet points
            if re.match(r'^[\*\-\+]\s+', line):
                # Flush current paragraph first
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    elements.append(Paragraph(self._convert_inline_markdown(para_text), self.styles['Normal']))
                    current_paragraph = []
                
                # Extract bullet text
                bullet_text = re.sub(r'^[\*\-\+]\s+', '', line)
                bullet_html = f"• {self._convert_inline_markdown(bullet_text)}"
                
                # Create bullet style
                bullet_style = ParagraphStyle(
                    'Bullet',
                    parent=self.styles['Normal'],
                    leftIndent=20,
                    bulletIndent=10
                )
                
                elements.append(Paragraph(bullet_html, bullet_style))
                i += 1
                continue
            
            # Handle code blocks (skip them)
            if line.startswith('```'):
                # Skip until closing ```
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    i += 1
                i += 1
                continue
            
            # Regular text - accumulate for paragraph
            current_paragraph.append(line)
            i += 1
        
        # Flush any remaining paragraph
        if current_paragraph:
            para_text = ' '.join(current_paragraph)
            elements.append(Paragraph(self._convert_inline_markdown(para_text), self.styles['Normal']))
        
        return elements
    
    def _convert_inline_markdown(self, text: str) -> str:
        """Convert inline markdown (bold, italic, code) to HTML for ReportLab"""
        if not text:
            return ""
        
        # Escape XML special characters first
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Convert bold+italic
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
        
        # Convert bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
        
        # Convert italic
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
        
        # Convert inline code
        text = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', text)
        
        # Convert links (keep link text only)
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        
        return text
    
    def _extract_candidate_name(self, evaluation: Dict[str, Any]) -> str:
        """Extract candidate name from resume data"""
        # First, check if LLM-extracted name is available
        candidate_name = evaluation.get('candidate_name', '')
        if candidate_name and candidate_name.lower() != 'candidate':
            return candidate_name
        
        # Fallback: Try multiple sources and patterns
        sources = [
            evaluation.get('structured_info', ''),
            evaluation.get('raw_resume', ''),
            evaluation.get('evaluation', '')
        ]
        
        for source in sources:
            if not source:
                continue
                
            # Pattern 1: Explicit name fields (Name: John Doe, Candidate: Jane Smith)
            name_patterns = [
                r'(?:Name|Candidate|Full\s+Name)\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
                r'(?:Name|Candidate|Full\s+Name)\s*[:\-]\s*([A-Z][A-Z\s]+)',  # ALL CAPS names
                r'\*\*Name\*\*\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',  # Markdown bold
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, source, re.IGNORECASE | re.MULTILINE)
                if match:
                    name = match.group(1).strip()
                    # Validate it's not a common word
                    if name.lower() not in ['candidate', 'resume', 'cv', 'name', 'unknown']:
                        return name
        
        # Pattern 2: First line of resume (often contains name)
        raw_resume = evaluation.get('raw_resume', '')
        if raw_resume:
            lines = [line.strip() for line in raw_resume.split('\n') if line.strip()]
            
            # Check first 10 lines
            for line in lines[:10]:
                # Skip lines that look like headers or labels
                if any(word in line.lower() for word in ['resume', 'curriculum', 'vitae', 'cv', 'profile', 'contact', 'email', 'phone']):
                    continue
                
                # Look for name-like patterns
                # Pattern: First Last or First Middle Last
                name_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})$', line)
                if name_match:
                    return name_match.group(1)
                
                # Pattern: ALL CAPS name
                if line.isupper() and 2 <= len(line.split()) <= 4 and len(line) <= 50:
                    # Convert to title case
                    return line.title()
                
                # Pattern: Title case name at start of line
                words = line.split()
                if len(words) >= 2 and len(words) <= 4:
                    if all(word[0].isupper() and word[1:].islower() for word in words if word):
                        # Check if words are reasonable length for names (2-20 chars each)
                        if all(2 <= len(word) <= 20 for word in words):
                            return ' '.join(words)
        
        return "Candidate"
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Section Header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#4338ca'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Subsection
        self.styles.add(ParagraphStyle(
            name='SubSection',
            parent=self.styles['Heading3'],
            fontSize=13,
            textColor=colors.HexColor('#6366f1'),
            spaceAfter=8
        ))
        
        # Score style
        self.styles.add(ParagraphStyle(
            name='ScoreStyle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#059669'),
            alignment=TA_CENTER
        ))
    
    def generate_full_report(
        self,
        evaluation: Dict[str, Any],
        github_analysis: Optional[Dict[str, Any]] = None,
        final_verdict: Optional[Dict[str, Any]] = None
    ) -> BytesIO:
        """
        Generate complete evaluation report as PDF
        
        Args:
            evaluation: Level 1 (Resume) evaluation data
            github_analysis: Level 2 (GitHub) analysis data (optional)
            final_verdict: Final verdict data (optional)
            
        Returns:
            BytesIO object containing PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        
        # Extract candidate name
        candidate_name = self._extract_candidate_name(evaluation)
        
        # Title
        title = Paragraph("Candidate Evaluation Report", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.1*inch))
        
        # Candidate Name
        name_para = Paragraph(f"<b>Candidate:</b> {candidate_name}", self.styles['Heading3'])
        story.append(name_para)
        story.append(Spacer(1, 0.2*inch))
        
        # Metadata
        date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        metadata = Paragraph(f"<i>Generated on {date_str}</i>", self.styles['Normal'])
        story.append(metadata)
        story.append(Spacer(1, 0.4*inch))
        
        # Executive Summary (if final verdict exists)
        if final_verdict:
            story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
            
            decision = final_verdict.get('decision', 'NO_HIRE')
            confidence = final_verdict.get('confidence', 'Medium')
            composite_score = final_verdict.get('composite_score', 0)
            
            # Decision table
            decision_color = colors.HexColor('#059669') if decision == 'HIRE' else colors.HexColor('#dc2626')
            decision_text = "✓ HIRE" if decision == 'HIRE' else "✗ NO HIRE"
            
            summary_data = [
                ['Final Decision', decision_text],
                ['Composite Score', f"{composite_score}/10"],
                ['Confidence Level', confidence]
            ]
            
            summary_table = Table(summary_data, colWidths=[2.5*inch, 4*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (1, 0), (1, 0), decision_color),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 10),
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Level 1: Resume Evaluation
        story.append(Paragraph("Level 1: Resume Evaluation", self.styles['SectionHeader']))
        
        l1_score = evaluation.get('score', 0)
        l1_max = evaluation.get('max_score', 10)
        l1_passed = evaluation.get('passed', False)
        l1_threshold = evaluation.get('threshold', 7)
        
        # L1 Score table
        l1_data = [
            ['Score', f"{l1_score}/{l1_max}"],
            ['Threshold', f"{l1_threshold}/10"],
            ['Status', 'PASSED ✓' if l1_passed else 'FAILED ✗']
        ]
        
        l1_table = Table(l1_data, colWidths=[2.5*inch, 4*inch])
        l1_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#dbeafe')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(l1_table)
        story.append(Spacer(1, 0.2*inch))
        
        # L1 Analysis (properly formatted markdown)
        story.append(Paragraph("<b>Analysis:</b>", self.styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        l1_analysis_raw = evaluation.get('evaluation', '')
        l1_elements = self._markdown_to_pdf_elements(l1_analysis_raw[:4000])  # Limit text
        for element in l1_elements:
            story.append(element)
        story.append(Spacer(1, 0.3*inch))
        
        # Level 2: GitHub Analysis (if available)
        if github_analysis:
            story.append(Paragraph("Level 2: GitHub Analysis", self.styles['SectionHeader']))
            
            l2_score = github_analysis.get('score', 0)
            l2_max = github_analysis.get('max_score', 10)
            l2_passed = github_analysis.get('passed', False)
            l2_threshold = github_analysis.get('threshold', 6)
            github_url = github_analysis.get('github_url', 'N/A')
            
            # L2 Score table
            l2_data = [
                ['GitHub Profile', github_url],
                ['Score', f"{l2_score}/{l2_max}"],
                ['Threshold', f"{l2_threshold}/10"],
                ['Status', 'PASSED ✓' if l2_passed else 'FAILED ✗']
            ]
            
            l2_table = Table(l2_data, colWidths=[2.5*inch, 4*inch])
            l2_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#d1fae5')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(l2_table)
            story.append(Spacer(1, 0.2*inch))
            
            # L2 Analysis (properly formatted markdown)
            story.append(Paragraph("<b>Analysis:</b>", self.styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
            l2_analysis_raw = github_analysis.get('analysis', '')
            l2_elements = self._markdown_to_pdf_elements(l2_analysis_raw[:4000])  # Limit text
            for element in l2_elements:
                story.append(element)
            story.append(Spacer(1, 0.3*inch))
        
        # Final Verdict Details (if available)
        if final_verdict:
            story.append(PageBreak())
            story.append(Paragraph("Final Verdict - Detailed Analysis", self.styles['SectionHeader']))
            story.append(Spacer(1, 0.1*inch))
            
            verdict_text_raw = final_verdict.get('verdict_text', '')
            verdict_elements = self._markdown_to_pdf_elements(verdict_text_raw[:5000])  # Limit text
            for element in verdict_elements:
                story.append(element)
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        footer_text = "<i>Generated by Tech Hiring Agentic Framework | Powered by Google ADK</i>"
        footer = Paragraph(footer_text, self.styles['Normal'])
        story.append(footer)
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer


# Create global instance
pdf_generator = PDFReportGenerator()
