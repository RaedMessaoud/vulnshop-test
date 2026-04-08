#!/usr/bin/env python3
"""
DevSecOps Security Report Generator
Parses security scan results (Bandit, Safety, DAST) and generates a formatted Markdown report
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

class SecurityReportGenerator:
    def __init__(self):
        self.report_lines = []
        self.vulnerabilities = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': [],
            'info': []
        }
        self.stats = {
            'total_issues': 0,
            'critical_count': 0,
            'high_count': 0,
            'medium_count': 0,
            'low_count': 0,
            'dependencies_checked': 0,
            'vulnerable_dependencies': 0
        }

    def parse_bandit_results(self, json_file='bandit-report.json') -> bool:
        """Parse Bandit SAST scan results"""
        if not os.path.exists(json_file):
            print(f"⚠️  Bandit report not found: {json_file}")
            return False
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            results = data.get('results', [])
            if not results:
                self.report_lines.append("✅ **SAST (Bandit)**: No vulnerabilities found")
                return True
            
            for issue in results:
                severity = issue.get('severity', 'MEDIUM').lower()
                confidence = issue.get('confidence', 'MEDIUM').lower()
                
                # Map Bandit severity to our severity levels
                if severity == 'high':
                    level = 'critical' if confidence == 'high' else 'high'
                elif severity == 'medium':
                    level = 'medium'
                else:
                    level = 'low'
                
                vuln = {
                    'type': 'SAST (Bandit)',
                    'test_id': issue.get('test_id', 'N/A'),
                    'test_name': issue.get('test_name', 'Unknown'),
                    'issue_text': issue.get('issue_text', ''),
                    'line_number': issue.get('line_number', 'N/A'),
                    'filename': issue.get('filename', 'N/A'),
                    'severity': level,
                    'code': issue.get('code', '')
                }
                self.vulnerabilities[level].append(vuln)
                self.stats['total_issues'] += 1
            
            return True
        except Exception as e:
            print(f"❌ Error parsing Bandit results: {e}")
            return False

    def parse_safety_results(self, output_file='safety-output.txt') -> bool:
        """Parse Safety dependency check results"""
        if not os.path.exists(output_file):
            print(f"⚠️  Safety report not found: {output_file}")
            return False
        
        try:
            with open(output_file, 'r') as f:
                content = f.read()
            
            # Check if vulnerabilities were found
            if 'No known security vulnerabilities' in content or 'safety check' in content and '0 vulnerabilities' in content.lower():
                self.report_lines.append("✅ **SCA (Safety)**: All dependencies are secure")
                return True
            
            # Parse vulnerability lines
            lines = content.split('\n')
            vuln_count = 0
            for i, line in enumerate(lines):
                if 'Vulnerability' in line or 'CVE' in line or 'insecure' in line.lower():
                    vuln = {
                        'type': 'SCA (Safety)',
                        'issue_text': line.strip(),
                        'severity': 'high',
                    }
                    self.vulnerabilities['high'].append(vuln)
                    vuln_count += 1
                    self.stats['total_issues'] += 1
            
            if vuln_count > 0:
                self.stats['vulnerable_dependencies'] = vuln_count
            
            return True
        except Exception as e:
            print(f"❌ Error parsing Safety results: {e}")
            return False

    def parse_dast_results(self, output_file='dast-results.txt') -> bool:
        """Parse DAST (Dynamic Application Security Testing) results"""
        if not os.path.exists(output_file):
            print(f"⚠️  DAST report not found: {output_file}")
        else:
            try:
                with open(output_file, 'r') as f:
                    content = f.read()
                
                # Parse DAST test results
                if '❌ VULNERABILITY' in content:
                    # Count vulnerabilities found
                    vuln_lines = [l for l in content.split('\n') if '❌ VULNERABILITY' in l]
                    for line in vuln_lines:
                        issue_text = line.replace('❌ VULNERABILITY:', '').replace('❌ VULNERABILITY [HIGH]:', '').replace('❌ VULNERABILITY [CRITICAL]:', '').strip()
                        
                        # Determine severity based on content
                        if 'UNION' in issue_text or 'data extraction' in issue_text.lower():
                            severity = 'critical'
                        else:
                            severity = 'high'
                        
                        vuln = {
                            'type': 'DAST (Dynamic Testing)',
                            'issue_text': issue_text,
                            'severity': severity,
                        }
                        self.vulnerabilities[severity].append(vuln)
                        self.stats['total_issues'] += 1
                
                # Also parse medium severity issues if present
                if '⚠️' in content and 'vulnerability' in content.lower():
                    med_lines = [l for l in content.split('\n') if '⚠️' in l and 'vulnerability' in l.lower()]
                    for line in med_lines:
                        issue_text = line.replace('⚠️ ', '').strip()
                        vuln = {
                            'type': 'DAST (Dynamic Testing)',
                            'issue_text': issue_text,
                            'severity': 'medium',
                        }
                        self.vulnerabilities['medium'].append(vuln)
                        self.stats['total_issues'] += 1
                
                if self.stats['total_issues'] == 0:
                    # No vulnerabilities found via main parsing, still check for specific patterns
                    pass
                    
            except Exception as e:
                print(f"⚠️  Error parsing DAST results: {e}")
        
        # Also parse detailed vulnerabilities file if exists
        vuln_file = 'dast-vulnerabilities.txt'
        if os.path.exists(vuln_file):
            try:
                with open(vuln_file, 'r') as f:
                    content = f.read()
                
                if '❌' in content:
                    # Parse vulnerabilities from detailed file
                    vuln_lines = [l for l in content.split('\n') if '❌ VULNERABILITY [' in l]
                    for line in vuln_lines:
                        # Extract severity and issue text
                        if '[CRITICAL]' in line:
                            severity = 'critical'
                        elif '[HIGH]' in line:
                            severity = 'high'
                        else:
                            severity = 'high'
                        
                        issue_text = line.split(':', 1)[-1].strip() if ':' in line else line.strip()
                        vuln = {
                            'type': 'DAST (Dynamic Testing)',
                            'issue_text': issue_text,
                            'severity': severity,
                        }
                        # Check if not already added
                        if vuln not in self.vulnerabilities[severity]:
                            self.vulnerabilities[severity].append(vuln)
                            self.stats['total_issues'] += 1
                            
            except Exception as e:
                print(f"⚠️  Error parsing DAST vulnerabilities file: {e}")
        
        return True

    def update_statistics(self):
        """Update vulnerability counts by severity"""
        for level in ['critical', 'high', 'medium', 'low']:
            self.stats[f'{level}_count'] = len(self.vulnerabilities[level])

    def generate_header(self) -> List[str]:
        """Generate report header with metadata"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        lines = [
            "# 🔒 DevSecOps Security Report",
            "",
            f"**Generated:** {now}",
            f"**Repository:** {os.getenv('GITHUB_REPOSITORY', 'Unknown')}",
            f"**Branch:** {os.getenv('GITHUB_REF_NAME', 'Unknown')}",
            f"**Commit:** {os.getenv('GITHUB_SHA', 'Unknown')[:8]}",
            "",
        ]
        return lines

    def generate_summary(self) -> List[str]:
        """Generate vulnerability summary with statistics"""
        self.update_statistics()
        
        total = self.stats['total_issues']
        critical = self.stats['critical_count']
        high = self.stats['high_count']
        medium = self.stats['medium_count']
        low = self.stats['low_count']
        
        # Determine overall status
        if critical > 0:
            status = "🔴 **CRITICAL ISSUES FOUND**"
            status_color = "critical"
        elif high > 0:
            status = "🟠 **HIGH SEVERITY ISSUES FOUND**"
            status_color = "high"
        elif medium > 0:
            status = "🟡 **MEDIUM SEVERITY ISSUES FOUND**"
            status_color = "medium"
        elif low > 0:
            status = "🟢 **LOW SEVERITY ISSUES - REVIEW RECOMMENDED**"
            status_color = "low"
        else:
            status = "✅ **NO VULNERABILITIES DETECTED**"
            status_color = "clean"
        
        lines = [
            "## 📊 Security Summary",
            "",
            f"**Status:** {status}",
            "",
            "### Vulnerability Breakdown",
            "",
        ]
        
        # Add statistics table
        if total > 0:
            lines.extend([
                "| Severity | Count | Impact |",
                "|----------|-------|--------|",
                f"| 🔴 Critical | {critical} | Highest |",
                f"| 🟠 High | {high} | High |",
                f"| 🟡 Medium | {medium} | Medium |",
                f"| 🟢 Low | {low} | Low |",
                f"| **Total** | **{total}** | - |",
                "",
            ])
        else:
            lines.append("✅ All security checks passed - No issues found")
            lines.append("")
        
        return lines

    def generate_vulnerabilities_section(self) -> List[str]:
        """Generate detailed vulnerabilities section"""
        lines = ["## 🔍 Detailed Findings", ""]
        
        has_vulns = any(self.vulnerabilities[level] for level in self.vulnerabilities)
        
        if not has_vulns:
            lines.append("✅ No vulnerabilities detected")
            return lines
        
        # Critical vulnerabilities
        if self.vulnerabilities['critical']:
            lines.append("### 🔴 Critical Issues")
            lines.append("")
            for i, vuln in enumerate(self.vulnerabilities['critical'], 1):
                lines.extend(self._format_vulnerability(vuln, i))
        
        # High severity
        if self.vulnerabilities['high']:
            lines.append("### 🟠 High Severity Issues")
            lines.append("")
            for i, vuln in enumerate(self.vulnerabilities['high'], 1):
                lines.extend(self._format_vulnerability(vuln, i))
        
        # Medium severity
        if self.vulnerabilities['medium']:
            lines.append("### 🟡 Medium Severity Issues")
            lines.append("")
            for i, vuln in enumerate(self.vulnerabilities['medium'], 1):
                lines.extend(self._format_vulnerability(vuln, i))
        
        # Low severity
        if self.vulnerabilities['low']:
            lines.append("### 🟢 Low Severity Issues")
            lines.append("")
            for i, vuln in enumerate(self.vulnerabilities['low'], 1):
                lines.extend(self._format_vulnerability(vuln, i))
        
        return lines

    def _format_vulnerability(self, vuln: Dict, index: int) -> List[str]:
        """Format a single vulnerability entry"""
        lines = [f"**{index}. {vuln.get('type', 'Unknown')}**"]
        
        if 'test_name' in vuln:
            lines.append(f"- **Test:** {vuln['test_name']}")
        
        if 'test_id' in vuln:
            lines.append(f"- **ID:** {vuln['test_id']}")
        
        if 'filename' in vuln:
            lines.append(f"- **File:** {vuln['filename']}")
        
        if 'line_number' in vuln:
            lines.append(f"- **Line:** {vuln['line_number']}")
        
        lines.append(f"- **Description:** {vuln.get('issue_text', 'N/A')}")
        
        if 'code' in vuln and vuln['code']:
            lines.append(f"- **Code Preview:**")
            lines.append("```python")
            lines.append(vuln['code'][:200])
            lines.append("```")
        
        lines.append("")
        
        return lines

    def generate_recommendations(self) -> List[str]:
        """Generate remediation recommendations"""
        lines = [
            "## 💡 Remediation Recommendations",
            "",
        ]
        
        critical_count = self.stats['critical_count']
        high_count = self.stats['high_count']
        
        if critical_count > 0:
            lines.append(f"### 🔴 Critical Issues ({critical_count})")
            lines.append("")
            lines.extend([
                "**Immediate Action Required:**",
                "- Halt deployment and fix critical vulnerabilities before production",
                "- Review SAST findings in Bandit output for specific code locations",
                "- Apply security patches immediately",
                "- Conduct code review with focus on identified issues",
                "",
            ])
        
        if high_count > 0:
            lines.append(f"### 🟠 High Severity Issues ({high_count})")
            lines.append("")
            lines.extend([
                "**Urgent Action Required:**",
                "- Fix high-severity issues before next release",
                "- Review input validation and output encoding",
                "- Check for missing authentication/authorization controls",
                "- Update vulnerable dependencies in requirements.txt",
                "",
            ])
        
        if self.stats['medium_count'] > 0:
            lines.append("### 🟡 Medium Issues")
            lines.extend([
                "- Address in the next sprint",
                "- Could allow attackers to gain partial access",
                "",
            ])
        
        lines.extend([
            "### 📋 General Security Best Practices",
            "- Always use parameterized queries to prevent SQL injection",
            "- Validate and sanitize all user inputs",
            "- Use strong authentication mechanisms (no hardcoded credentials)",
            "- Implement proper error handling (don't reveal system information)",
            "- Keep all dependencies updated",
            "- Use HTTPS for all communications",
            "- Implement security headers (CSP, X-Frame-Options, etc.)",
            "",
        ])
        
        return lines

    def generate_tools_info(self) -> List[str]:
        """Generate information about security tools used"""
        lines = [
            "## 🛠️ Security Tools Used",
            "",
            "### SAST (Static Application Security Testing)",
            "- **Tool:** Bandit",
            "- **Purpose:** Scans Python code for common security vulnerabilities",
            "- **Coverage:** Code analysis, hard-coded credentials, weak cryptography",
            "",
            "### SCA (Software Composition Analysis)",
            "- **Tool:** Safety",
            "- **Purpose:** Checks Python dependencies for known vulnerabilities",
            "- **Coverage:** CVE database, vulnerable package versions",
            "",
            "### DAST (Dynamic Application Security Testing)",
            "- **Tool:** Custom pytest tests",
            "- **Purpose:** Runtime testing of application behavior",
            "- **Coverage:** SQL injection, authentication bypass, authorization issues",
            "",
        ]
        return lines

    def generate_footer(self) -> List[str]:
        """Generate report footer"""
        lines = [
            "---",
            f"📅 Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "🔐 DevSecOps Pipeline - Continuous Security Scanning",
            "For more information, see: https://owasp.org/",
        ]
        return lines

    def generate_full_report(self) -> str:
        """Generate complete security report"""
        sections = []
        
        # Build report sections
        sections.extend(self.generate_header())
        sections.extend(self.generate_summary())
        sections.extend(self.generate_vulnerabilities_section())
        sections.extend(self.generate_recommendations())
        sections.extend(self.generate_tools_info())
        sections.extend(self.generate_footer())
        
        return "\n".join(sections)

    def save_report(self, filename='SECURITY_REPORT.md'):
        """Save report to file"""
        report = self.generate_full_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        return filename

    def print_report(self):
        """Print report to stdout"""
        report = self.generate_full_report()
        print(report)


def main():
    """Main entry point"""
    generator = SecurityReportGenerator()
    
    # Parse all available scan results
    print("🔍 Parsing security scan results...")
    print("")
    
    bandit_ok = generator.parse_bandit_results()
    safety_ok = generator.parse_safety_results()
    dast_ok = generator.parse_dast_results()
    
    # Generate and display report
    print("📊 Generating security report...")
    print("")
    print("=" * 80)
    generator.print_report()
    print("=" * 80)
    print("")
    
    # Save report to file
    report_file = generator.save_report()
    print(f"✅ Report saved to: {report_file}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
