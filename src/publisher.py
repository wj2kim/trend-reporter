"""GitHub Pages 퍼블리셔"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import pytz


class GitHubPagesPublisher:
    """리포트를 GitHub Pages용 HTML로 저장"""

    def __init__(self, docs_dir: Optional[str] = None):
        project_root = Path(__file__).parent.parent
        self.docs_dir = Path(docs_dir) if docs_dir else project_root / "docs"
        self.reports_dir = self.docs_dir / "reports"
        self.index_file = self.docs_dir / "index.html"
        self.reports_json = self.docs_dir / "reports.json"

    def publish(self, title: str, content: str) -> bool:
        """리포트를 HTML로 저장"""
        try:
            # 디렉토리 생성
            self.docs_dir.mkdir(exist_ok=True)
            self.reports_dir.mkdir(exist_ok=True)

            # 파일명 생성 (날짜 기반)
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            filename = now.strftime("%Y-%m-%d-%H%M") + ".html"
            filepath = self.reports_dir / filename

            # HTML 생성
            html = self._generate_html(title, content, now)
            filepath.write_text(html, encoding='utf-8')
            print(f"[Publisher] 리포트 저장: {filepath}")

            # 인덱스 업데이트
            self._update_index(title, filename, now)

            return True

        except Exception as e:
            print(f"[Publisher] 저장 실패: {e}")
            return False

    def _generate_html(self, title: str, content: str, timestamp: datetime) -> str:
        """마크다운 컨텐츠를 HTML로 변환"""
        html_content = self._md_to_html(content)
        date_str = timestamp.strftime("%Y-%m-%d %H:%M")

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            line-height: 1.7;
            color: #1a1a1a;
            background: #fafafa;
        }}
        .header {{
            background: #fff;
            border-bottom: 1px solid #eee;
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .header-inner {{
            max-width: 720px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .back-link {{
            color: #666;
            text-decoration: none;
            font-size: 14px;
            transition: color 0.2s;
        }}
        .back-link:hover {{ color: #000; }}
        .timestamp {{
            color: #888;
            font-size: 13px;
        }}
        .container {{
            max-width: 720px;
            margin: 0 auto;
            padding: 40px 24px 80px;
        }}
        h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #000;
            margin-bottom: 48px;
            letter-spacing: -0.5px;
        }}
        h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #000;
            margin-top: 48px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid #eee;
        }}
        h3 {{
            font-size: 15px;
            font-weight: 600;
            color: #444;
            margin-top: 28px;
            margin-bottom: 12px;
        }}
        p {{
            margin-bottom: 16px;
            color: #333;
        }}
        ul, ol {{
            margin-left: 20px;
            margin-bottom: 20px;
        }}
        li {{
            margin-bottom: 10px;
            color: #333;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        strong {{
            font-weight: 600;
            color: #000;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 14px;
            font-family: 'SF Mono', Consolas, monospace;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-inner">
            <a href="../index.html" class="back-link">< Back</a>
            <span class="timestamp">{date_str}</span>
        </div>
    </div>
    <div class="container">
        <h1>{title}</h1>
        <div class="content">
            {html_content}
        </div>
    </div>
</body>
</html>"""

    def _md_to_html(self, md: str) -> str:
        """간단한 마크다운 → HTML 변환"""
        import re

        lines = md.split('\n')
        html_lines = []
        in_list = False
        list_type = None

        for line in lines:
            stripped = line.strip()

            # 빈 줄
            if not stripped:
                if in_list:
                    html_lines.append(f'</{list_type}>')
                    in_list = False
                html_lines.append('')
                continue

            # 헤더
            if stripped.startswith('### '):
                if in_list:
                    html_lines.append(f'</{list_type}>')
                    in_list = False
                html_lines.append(f'<h3>{stripped[4:]}</h3>')
                continue
            if stripped.startswith('## '):
                if in_list:
                    html_lines.append(f'</{list_type}>')
                    in_list = False
                html_lines.append(f'<h2>{stripped[3:]}</h2>')
                continue
            if stripped.startswith('# '):
                if in_list:
                    html_lines.append(f'</{list_type}>')
                    in_list = False
                html_lines.append(f'<h2>{stripped[2:]}</h2>')
                continue

            # 리스트
            if stripped.startswith('- ') or stripped.startswith('* '):
                if not in_list or list_type != 'ul':
                    if in_list:
                        html_lines.append(f'</{list_type}>')
                    html_lines.append('<ul>')
                    in_list = True
                    list_type = 'ul'
                item = self._inline_format(stripped[2:])
                html_lines.append(f'<li>{item}</li>')
                continue

            # 숫자 리스트
            if re.match(r'^\d+\.\s', stripped):
                if not in_list or list_type != 'ol':
                    if in_list:
                        html_lines.append(f'</{list_type}>')
                    html_lines.append('<ol>')
                    in_list = True
                    list_type = 'ol'
                item = self._inline_format(re.sub(r'^\d+\.\s', '', stripped))
                html_lines.append(f'<li>{item}</li>')
                continue

            # 일반 텍스트
            if in_list:
                html_lines.append(f'</{list_type}>')
                in_list = False
            html_lines.append(f'<p>{self._inline_format(stripped)}</p>')

        if in_list:
            html_lines.append(f'</{list_type}>')

        return '\n'.join(html_lines)

    def _inline_format(self, text: str) -> str:
        """인라인 마크다운 변환 (볼드, 링크 등)"""
        import re
        # 볼드
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # 링크
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank">\1</a>', text)
        # 인라인 코드
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        return text

    def _update_index(self, title: str, filename: str, timestamp: datetime):
        """인덱스 페이지 업데이트"""
        # 기존 리포트 목록 로드
        reports = []
        if self.reports_json.exists():
            try:
                reports = json.loads(self.reports_json.read_text(encoding='utf-8'))
            except:
                pass

        # 새 리포트 추가
        reports.insert(0, {
            "title": title,
            "filename": filename,
            "date": timestamp.strftime("%Y-%m-%d"),
            "time": timestamp.strftime("%H:%M")
        })

        # 최근 30개만 유지
        reports = reports[:30]

        # JSON 저장
        self.reports_json.write_text(
            json.dumps(reports, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        # index.html 생성
        self._generate_index(reports)

    def _generate_index(self, reports: list):
        """인덱스 HTML 생성"""
        import re
        report_items = ""
        for r in reports:
            # 제목 그대로 사용 (이모지는 이제 생성 안 됨)
            title = r['title']
            date_time = f"{r['date']} {r['time']}"
            report_items += f"""
                <a href="reports/{r['filename']}" class="report-item">
                    <span class="title">{title}</span>
                    <span class="date">{date_time}</span>
                </a>"""

        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trend Reporter</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            background: #fff;
            min-height: 100vh;
        }}
        .container {{
            max-width: 640px;
            margin: 0 auto;
            padding: 80px 24px;
        }}
        h1 {{
            font-size: 32px;
            font-weight: 700;
            color: #000;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }}
        .subtitle {{
            color: #666;
            font-size: 15px;
            margin-bottom: 48px;
        }}
        .report-list {{
            display: flex;
            flex-direction: column;
        }}
        .report-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid #eee;
            text-decoration: none;
            transition: opacity 0.2s;
        }}
        .report-item:hover {{
            opacity: 0.6;
        }}
        .title {{
            color: #000;
            font-size: 15px;
            font-weight: 500;
        }}
        .date {{
            color: #888;
            font-size: 13px;
            flex-shrink: 0;
            margin-left: 16px;
        }}
        .empty {{
            color: #888;
            padding: 40px 0;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Trend Reporter</h1>
        <p class="subtitle">Daily Tech & Market Trends</p>
        <div class="report-list">
            {report_items if report_items else '<p class="empty">No reports yet.</p>'}
        </div>
    </div>
</body>
</html>"""

        self.index_file.write_text(html, encoding='utf-8')
        print(f"[Publisher] 인덱스 업데이트: {self.index_file}")
