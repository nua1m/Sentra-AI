from fpdf import FPDF
import os
import re
from datetime import datetime

def sanitize_text(text: str) -> str:
    """Remove non-Latin1 characters that FPDF can't handle."""
    if not text:
        return ""
    # Replace common unicode with ASCII equivalents
    replacements = {
        '•': '-',
        '–': '-',
        '—': '-',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '⛔': '[X]',
        '✔': '[OK]',
        '✓': '[OK]',
        '❌': '[X]',
        '🎯': '*',
        '🛡️': '*',
        '⚡': '*',
    }
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    # Remove any remaining non-latin1 characters
    return text.encode('latin-1', 'ignore').decode('latin-1')

class AuditReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Sentra.AI - Security Audit Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf_report(scan_data: dict, filename: str = "report.pdf") -> str:
    """
    Generates a PDF report from scan results.
    """
    pdf = AuditReport()
    pdf.add_page()
    
    # Metadata
    target = sanitize_text(scan_data.get('target', 'Unknown'))
    scan_id = sanitize_text(str(scan_data.get('scan_id', 'N/A')))
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Target: {target}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 10, f"Scan ID: {scan_id}", ln=True)
    pdf.ln(10)
    
    # AI Analysis Section
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Executive Summary (AI Analysis)", ln=True)
    pdf.set_font("Arial", "", 11)
    
    analysis = scan_data.get("analysis", "No analysis available.")
    analysis = sanitize_text(analysis.replace("**", "").replace("__", ""))
    pdf.multi_cell(0, 7, analysis)
    pdf.ln(10)
    
    # Raw Nmap Data
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Technical Details (Nmap)", ln=True)
    pdf.set_font("Courier", "", 9)
    nmap_data = sanitize_text(scan_data.get("nmap", "No Nmap data."))
    pdf.multi_cell(0, 5, nmap_data[:5000])
    
    # Raw Nikto Data
    nikto_data = scan_data.get("nikto", "")
    if nikto_data and len(nikto_data.strip()) > 10:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Web Vulnerabilities (Nikto)", ln=True)
        pdf.set_font("Courier", "", 9)
        pdf.multi_cell(0, 5, sanitize_text(nikto_data)[:5000])

    # Save
    report_path = os.path.join(os.getcwd(), filename)
    pdf.output(report_path)
    return report_path
