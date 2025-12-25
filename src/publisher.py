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
        # 간단한 마크다운 → HTML 변환
        html_content = self._md_to_html(content)

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 25px;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #3498db;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        p {{ margin-bottom: 15px; }}
        ul, ol {{
            margin-left: 20px;
            margin-bottom: 15px;
        }}
        li {{ margin-bottom: 8px; }}
        a {{ color: #3498db; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .timestamp {{
            color: #95a5a6;
            font-size: 0.9em;
            margin-bottom: 20px;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            padding: 8px 16px;
            background: #ecf0f1;
            border-radius: 5px;
        }}
        strong {{ color: #2c3e50; }}
        code {{
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="../index.html" class="back-link">&larr; 목록으로</a>
        <h1>{title}</h1>
        <p class="timestamp">{timestamp.strftime("%Y년 %m월 %d일 %H:%M")} KST</p>
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
        report_items = ""
        for r in reports:
            report_items += f"""
            <li>
                <a href="reports/{r['filename']}">{r['title']}</a>
                <span class="date">{r['date']} {r['time']}</span>
            </li>"""

        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trend Reporter</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 700px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2em;
        }}
        .subtitle {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
        }}
        ul {{
            list-style: none;
        }}
        li {{
            padding: 15px;
            border-bottom: 1px solid #ecf0f1;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        li:hover {{
            background: #f8f9fa;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .date {{
            color: #95a5a6;
            font-size: 0.9em;
        }}
        .empty {{
            text-align: center;
            color: #95a5a6;
            padding: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Trend Reporter</h1>
        <p class="subtitle">Daily Tech & Market Trends</p>
        <ul>
            {report_items if report_items else '<li class="empty">아직 리포트가 없습니다.</li>'}
        </ul>
    </div>
</body>
</html>"""

        self.index_file.write_text(html, encoding='utf-8')
        print(f"[Publisher] 인덱스 업데이트: {self.index_file}")
