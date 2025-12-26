"""GitHub Pages 퍼블리셔 - SEO/GEO/AEO 최적화"""

import os
import json
import re
import html
from datetime import datetime
from pathlib import Path
from typing import Optional
import pytz


class GitHubPagesPublisher:
    """리포트를 GitHub Pages용 HTML로 저장 (SEO 최적화)"""

    # 사이트 설정
    SITE_URL = "https://wj2kim.github.io/trend-reporter"
    SITE_NAME = "Trend Reporter"
    SITE_DESCRIPTION = "AI 기반 글로벌 트렌드 리포트 - 매일 세계 정세, 주식 시장, 개발, AI 트렌드를 분석하여 한국어로 제공합니다."
    SITE_AUTHOR = "Trend Reporter"
    SITE_LANGUAGE = "ko"
    SITE_LOGO = "https://wj2kim.github.io/trend-reporter/og-image.svg"

    def __init__(self, docs_dir: Optional[str] = None):
        project_root = Path(__file__).parent.parent
        self.docs_dir = Path(docs_dir) if docs_dir else project_root / "docs"
        self.reports_dir = self.docs_dir / "reports"
        self.index_file = self.docs_dir / "index.html"
        self.reports_json = self.docs_dir / "reports.json"
        self.sitemap_file = self.docs_dir / "sitemap.xml"
        self.robots_file = self.docs_dir / "robots.txt"
        self.feed_file = self.docs_dir / "feed.xml"

    def publish(self, title: str, content: str, category: str = "general",
                keywords: list = None) -> bool:
        """리포트를 HTML로 저장

        Args:
            title: 리포트 제목
            content: 리포트 내용 (마크다운)
            category: 카테고리 ("market" | "dev" | "general")
            keywords: 키워드 리스트
        """
        if keywords is None:
            keywords = []
        try:
            # 디렉토리 생성
            self.docs_dir.mkdir(exist_ok=True)
            self.reports_dir.mkdir(exist_ok=True)

            # 파일명 생성 (날짜 + 카테고리 기반)
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            filename = now.strftime("%Y-%m-%d-%H%M") + f"-{category}.html"
            filepath = self.reports_dir / filename

            # 메타 설명 추출
            description = self._extract_description(content)

            # 읽기 시간 계산
            reading_time = self._calculate_reading_time(content)

            # HTML 생성
            report_html = self._generate_html(title, content, now, category, filename, description, reading_time)
            filepath.write_text(report_html, encoding='utf-8')
            print(f"[Publisher] 리포트 저장: {filepath}")

            # 인덱스 업데이트
            self._update_index(title, filename, now, category, description, reading_time, keywords)

            # robots.txt 생성 (없으면)
            self._generate_robots()

            return True

        except Exception as e:
            print(f"[Publisher] 저장 실패: {e}")
            return False

    def _calculate_reading_time(self, content: str) -> int:
        """콘텐츠 읽기 시간 계산 (분 단위)"""
        # 마크다운 제거
        text = re.sub(r'#{1,6}\s+', '', content)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        text = re.sub(r'[•\-\*]\s+', '', text)

        # 글자 수 기준 (한국어는 분당 약 500자)
        char_count = len(text.replace(' ', '').replace('\n', ''))
        reading_time = max(1, round(char_count / 500))
        return reading_time

    def _extract_description(self, content: str, max_length: int = 160) -> str:
        """콘텐츠에서 메타 설명 추출"""
        # 마크다운 제거
        text = re.sub(r'#{1,6}\s+', '', content)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        text = re.sub(r'[•\-\*]\s+', '', text)
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        return html.escape(text)

    def _generate_html(self, title: str, content: str, timestamp: datetime,
                       category: str, filename: str, description: str,
                       reading_time: int = 1) -> str:
        """마크다운 컨텐츠를 SEO 최적화 HTML로 변환"""
        html_content = self._md_to_html(content)
        date_str = timestamp.strftime("%Y-%m-%d %H:%M")
        iso_date = timestamp.isoformat()
        category_label = "Market" if category == "market" else "Dev" if category == "dev" else "Report"
        category_full = "세계 정세 & 주식 시장" if category == "market" else "개발 & AI 트렌드" if category == "dev" else "트렌드 리포트"
        reading_time_str = f"{reading_time}분"
        reading_time_en = f"{reading_time} min read"
        # 영문 날짜 포맷 (Oct 20, 2025)
        date_en = timestamp.strftime("%b %d, %Y")

        canonical_url = f"{self.SITE_URL}/reports/{filename}"
        # 타이틀에서 날짜 부분 제거 (예: "제목 | 2025-12-26 15:33" -> "제목")
        display_title = title.split(" | ")[0] if " | " in title else title
        escaped_title = html.escape(display_title)
        escaped_desc = html.escape(description)

        # JSON-LD 구조화 데이터 (NewsArticle)
        json_ld = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": title,
            "description": description,
            "image": self.SITE_LOGO,
            "datePublished": iso_date,
            "dateModified": iso_date,
            "author": {
                "@type": "Organization",
                "name": self.SITE_AUTHOR,
                "url": self.SITE_URL
            },
            "publisher": {
                "@type": "Organization",
                "name": self.SITE_NAME,
                "logo": {
                    "@type": "ImageObject",
                    "url": self.SITE_LOGO
                }
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": canonical_url
            },
            "articleSection": category_full,
            "inLanguage": self.SITE_LANGUAGE,
            "isAccessibleForFree": True
        }

        return f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- Search Console Verification -->
    <meta name="google-site-verification" content="SoecC62RmfwaJ6jbdXplSnQFsHqZrjrt-q1vf_csCTI" />
    <meta name="naver-site-verification" content="78fcf466a31099b2a6c05d132e46b1f5fb9e14f5" />

    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-BZ704XQ445"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', 'G-BZ704XQ445');
    </script>

    <!-- Primary Meta Tags -->
    <title>{escaped_title} | {self.SITE_NAME}</title>
    <meta name="title" content="{escaped_title} | {self.SITE_NAME}">
    <meta name="description" content="{escaped_desc}">
    <meta name="author" content="{self.SITE_AUTHOR}">
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
    <meta name="keywords" content="{category_full}, 트렌드 리포트, {category_label}, AI 분석, 글로벌 트렌드, 한국어 리포트">
    <link rel="canonical" href="{canonical_url}">
    <link rel="alternate" type="application/rss+xml" title="{self.SITE_NAME} RSS Feed" href="{self.SITE_URL}/feed.xml">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="{canonical_url}">
    <meta property="og:title" content="{escaped_title}">
    <meta property="og:description" content="{escaped_desc}">
    <meta property="og:image" content="{self.SITE_LOGO}">
    <meta property="og:site_name" content="{self.SITE_NAME}">
    <meta property="og:locale" content="ko_KR">
    <meta property="article:published_time" content="{iso_date}">
    <meta property="article:modified_time" content="{iso_date}">
    <meta property="article:section" content="{category_full}">
    <meta property="article:author" content="{self.SITE_AUTHOR}">

    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="{canonical_url}">
    <meta property="twitter:title" content="{escaped_title}">
    <meta property="twitter:description" content="{escaped_desc}">
    <meta property="twitter:image" content="{self.SITE_LOGO}">

    <!-- JSON-LD Structured Data -->
    <script type="application/ld+json">
{json.dumps(json_ld, ensure_ascii=False, indent=4)}
    </script>

    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            line-height: 1.7;
            color: #1a1a1a;
            background: #fafafa;
        }}
        header {{
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
        .header-right {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .category-badge {{
            background: #f0f0f0;
            color: #555;
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 12px;
            font-weight: 500;
        }}
        time {{
            color: #888;
            font-size: 13px;
        }}
        .reading-time {{
            color: #888;
            font-size: 13px;
            padding-right: 12px;
            border-right: 1px solid #ddd;
        }}
        main {{
            max-width: 720px;
            margin: 0 auto;
            padding: 40px 24px 80px;
        }}
        article {{}}
        h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #000;
            margin-bottom: 12px;
            letter-spacing: -0.5px;
        }}
        .article-meta {{
            color: #888;
            font-size: 14px;
            margin-bottom: 48px;
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
    <header>
        <nav class="header-inner" aria-label="breadcrumb">
            <a href="../index.html" class="back-link" aria-label="리포트 목록으로 돌아가기">&lt; Back</a>
            <div class="header-right">
                <span class="category-badge">{category_label}</span>
                <span class="reading-time">{reading_time_str} read</span>
                <time datetime="{iso_date}">{date_str}</time>
            </div>
        </nav>
    </header>
    <main>
        <article itemscope itemtype="https://schema.org/NewsArticle">
            <meta itemprop="datePublished" content="{iso_date}">
            <meta itemprop="dateModified" content="{iso_date}">
            <meta itemprop="author" content="{self.SITE_AUTHOR}">
            <h1 itemprop="headline">{escaped_title}</h1>
            <p class="article-meta">{reading_time_en}  ·  {date_en}</p>
            <div class="content" itemprop="articleBody">
                {html_content}
            </div>
        </article>
    </main>
</body>
</html>'''

    def _md_to_html(self, md: str) -> str:
        """간단한 마크다운 → HTML 변환"""
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
                html_lines.append(f'<h3>{html.escape(stripped[4:])}</h3>')
                continue
            if stripped.startswith('## '):
                if in_list:
                    html_lines.append(f'</{list_type}>')
                    in_list = False
                html_lines.append(f'<h2>{html.escape(stripped[3:])}</h2>')
                continue
            if stripped.startswith('# '):
                if in_list:
                    html_lines.append(f'</{list_type}>')
                    in_list = False
                html_lines.append(f'<h2>{html.escape(stripped[2:])}</h2>')
                continue

            # 리스트 (• 포함)
            if stripped.startswith('- ') or stripped.startswith('* ') or stripped.startswith('• '):
                if not in_list or list_type != 'ul':
                    if in_list:
                        html_lines.append(f'</{list_type}>')
                    html_lines.append('<ul>')
                    in_list = True
                    list_type = 'ul'
                # 첫 문자 제거 (-, *, •)
                item_text = stripped[2:] if stripped[0] in '-*' else stripped[2:]
                item = self._inline_format(item_text)
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
        # HTML 이스케이프 먼저
        text = html.escape(text)
        # 볼드
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # 링크
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', text)
        # 인라인 코드
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        return text

    def _update_index(self, title: str, filename: str, timestamp: datetime,
                      category: str = "general", description: str = "",
                      reading_time: int = 1, keywords: list = None):
        """인덱스 페이지 업데이트"""
        if keywords is None:
            keywords = []

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
            "time": timestamp.strftime("%H:%M"),
            "category": category,
            "description": description,
            "reading_time": reading_time,
            "keywords": keywords
        })

        # 최근 50개만 유지 (두 카테고리이므로 넉넉하게)
        reports = reports[:50]

        # JSON 저장
        self.reports_json.write_text(
            json.dumps(reports, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        # index.html 생성
        self._generate_index(reports)

        # sitemap.xml 생성
        self._generate_sitemap(reports)

        # RSS feed 생성
        self._generate_feed(reports)

    def _generate_index(self, reports: list):
        """SEO 최적화 인덱스 HTML 생성"""
        report_items = ""
        item_list_elements = []

        for i, r in enumerate(reports):
            # 타이틀에서 날짜 부분 제거
            raw_title = r['title']
            display_title = raw_title.split(" | ")[0] if " | " in raw_title else raw_title
            title = html.escape(display_title)

            # 날짜 포맷 (Dec 26)
            try:
                from datetime import datetime as dt
                date_obj = dt.strptime(r['date'], "%Y-%m-%d")
                date_short = date_obj.strftime("%b %d")
            except:
                date_short = r['date']

            category = r.get('category', 'general')
            category_label = "Market" if category == "market" else "Dev" if category == "dev" else ""
            category_class = f"category-{category}" if category in ["market", "dev"] else ""

            # 키워드 태그 HTML
            keywords = r.get('keywords', [])
            keywords_html = ' '.join([f'<span class="tag">#{html.escape(k)}</span>' for k in keywords[:3]])

            badge_html = f'<span class="badge {category_class}">{category_label}</span>' if category_label else ""
            report_url = f"{self.SITE_URL}/reports/{r['filename']}"

            report_items += f'''
                <a href="reports/{r['filename']}" class="report-item" data-category="{category}">
                    <div class="item-left">
                        {badge_html}
                        <span class="title">{title}</span>
                        <span class="tags">{keywords_html}</span>
                    </div>
                    <time class="date" datetime="{r['date']}T{r['time']}:00+09:00">{date_short}</time>
                </a>'''

            # JSON-LD ItemList용
            item_list_elements.append({
                "@type": "ListItem",
                "position": i + 1,
                "url": report_url,
                "name": r['title']
            })

        # JSON-LD 구조화 데이터 (WebSite + ItemList)
        json_ld_website = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": self.SITE_NAME,
            "description": self.SITE_DESCRIPTION,
            "url": self.SITE_URL,
            "inLanguage": self.SITE_LANGUAGE,
            "publisher": {
                "@type": "Organization",
                "name": self.SITE_NAME,
                "logo": {
                    "@type": "ImageObject",
                    "url": self.SITE_LOGO
                }
            },
            "potentialAction": {
                "@type": "SearchAction",
                "target": f"{self.SITE_URL}/?q={{search_term_string}}",
                "query-input": "required name=search_term_string"
            }
        }

        json_ld_itemlist = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": "최신 트렌드 리포트",
            "description": "AI가 분석한 최신 글로벌 트렌드 리포트 목록",
            "numberOfItems": len(item_list_elements),
            "itemListElement": item_list_elements[:20]  # 최근 20개만
        }

        html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- Search Console Verification -->
    <meta name="google-site-verification" content="SoecC62RmfwaJ6jbdXplSnQFsHqZrjrt-q1vf_csCTI" />
    <meta name="naver-site-verification" content="78fcf466a31099b2a6c05d132e46b1f5fb9e14f5" />

    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-BZ704XQ445"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', 'G-BZ704XQ445');
    </script>

    <!-- Primary Meta Tags -->
    <title>{self.SITE_NAME} - AI 기반 글로벌 트렌드 리포트</title>
    <meta name="title" content="{self.SITE_NAME} - AI 기반 글로벌 트렌드 리포트">
    <meta name="description" content="{self.SITE_DESCRIPTION}">
    <meta name="author" content="{self.SITE_AUTHOR}">
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
    <meta name="keywords" content="트렌드 리포트, 세계 정세, 주식 시장, AI 트렌드, 개발 트렌드, 글로벌 뉴스, 한국어 리포트, AI 분석">
    <link rel="canonical" href="{self.SITE_URL}/">
    <link rel="alternate" type="application/rss+xml" title="{self.SITE_NAME} RSS Feed" href="{self.SITE_URL}/feed.xml">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{self.SITE_URL}/">
    <meta property="og:title" content="{self.SITE_NAME} - AI 기반 글로벌 트렌드 리포트">
    <meta property="og:description" content="{self.SITE_DESCRIPTION}">
    <meta property="og:image" content="{self.SITE_LOGO}">
    <meta property="og:site_name" content="{self.SITE_NAME}">
    <meta property="og:locale" content="ko_KR">

    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="{self.SITE_URL}/">
    <meta property="twitter:title" content="{self.SITE_NAME} - AI 기반 글로벌 트렌드 리포트">
    <meta property="twitter:description" content="{self.SITE_DESCRIPTION}">
    <meta property="twitter:image" content="{self.SITE_LOGO}">

    <!-- JSON-LD Structured Data -->
    <script type="application/ld+json">
{json.dumps(json_ld_website, ensure_ascii=False, indent=4)}
    </script>
    <script type="application/ld+json">
{json.dumps(json_ld_itemlist, ensure_ascii=False, indent=4)}
    </script>

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
        header {{
            margin-bottom: 32px;
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
        }}
        nav {{
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
            border-bottom: 1px solid #eee;
            padding-bottom: 16px;
        }}
        .filter-tab {{
            padding: 8px 16px;
            border: none;
            background: #f5f5f5;
            color: #666;
            font-size: 14px;
            font-weight: 500;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .filter-tab:hover {{
            background: #eee;
        }}
        .filter-tab.active {{
            background: #000;
            color: #fff;
        }}
        main {{
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
        .report-item.hidden {{
            display: none;
        }}
        .report-item:hover {{
            opacity: 0.6;
        }}
        .item-left {{
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 0;
        }}
        .badge {{
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 10px;
            font-weight: 500;
            flex-shrink: 0;
        }}
        .category-market {{
            background: #e8f4fc;
            color: #1a73e8;
        }}
        .category-dev {{
            background: #e6f4ea;
            color: #1e8e3e;
        }}
        .title {{
            color: #000;
            font-size: 15px;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .tags {{
            display: flex;
            gap: 6px;
            flex-shrink: 0;
            margin-left: 8px;
        }}
        .tag {{
            color: #888;
            font-size: 12px;
            font-weight: 400;
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
        .pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid #eee;
        }}
        .pagination button {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            background: #fff;
            color: #333;
            font-size: 14px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .pagination button:hover:not(:disabled) {{
            background: #f5f5f5;
            border-color: #ccc;
        }}
        .pagination button:disabled {{
            opacity: 0.4;
            cursor: not-allowed;
        }}
        .pagination button.active {{
            background: #000;
            color: #fff;
            border-color: #000;
        }}
        .pagination .page-info {{
            color: #888;
            font-size: 13px;
            margin: 0 8px;
        }}
        footer {{
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid #eee;
            color: #888;
            font-size: 13px;
            text-align: center;
        }}
        footer a {{
            color: #666;
            text-decoration: none;
        }}
        footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{self.SITE_NAME}</h1>
            <p class="subtitle">Daily Tech & Market Trends - AI가 분석하는 글로벌 트렌드</p>
        </header>
        <nav aria-label="리포트 카테고리 필터">
            <button class="filter-tab active" data-filter="all" aria-pressed="true">All</button>
            <button class="filter-tab" data-filter="market" aria-pressed="false">Market</button>
            <button class="filter-tab" data-filter="dev" aria-pressed="false">Dev</button>
        </nav>
        <main role="feed" aria-label="트렌드 리포트 목록">
            {report_items if report_items else '<p class="empty">No reports yet.</p>'}
        </main>
        <div class="pagination" id="pagination"></div>
        <footer>
            <p>Powered by AI - 매일 자동으로 글로벌 트렌드를 수집하고 분석합니다.</p>
            <p><a href="feed.xml">RSS Feed</a> · <a href="sitemap.xml">Sitemap</a></p>
        </footer>
    </div>
    <script>
        const ITEMS_PER_PAGE = 20;
        let currentPage = 1;
        let currentFilter = 'all';

        function getFilteredItems() {{
            const items = Array.from(document.querySelectorAll('.report-item'));
            if (currentFilter === 'all') return items;
            return items.filter(item => item.dataset.category === currentFilter);
        }}

        function renderPage() {{
            const allItems = Array.from(document.querySelectorAll('.report-item'));
            const filteredItems = getFilteredItems();
            const totalPages = Math.ceil(filteredItems.length / ITEMS_PER_PAGE);

            if (currentPage > totalPages) currentPage = totalPages || 1;

            const start = (currentPage - 1) * ITEMS_PER_PAGE;
            const end = start + ITEMS_PER_PAGE;

            allItems.forEach(item => item.classList.add('hidden'));
            filteredItems.slice(start, end).forEach(item => item.classList.remove('hidden'));

            renderPagination(totalPages);
        }}

        function renderPagination(totalPages) {{
            const container = document.getElementById('pagination');
            if (totalPages <= 1) {{
                container.innerHTML = '';
                return;
            }}

            let html = `<button onclick="goToPage(${{currentPage - 1}})" ${{currentPage === 1 ? 'disabled' : ''}}>&lt; Prev</button>`;

            const maxButtons = 5;
            let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
            let endPage = Math.min(totalPages, startPage + maxButtons - 1);
            if (endPage - startPage < maxButtons - 1) startPage = Math.max(1, endPage - maxButtons + 1);

            if (startPage > 1) html += `<button onclick="goToPage(1)">1</button><span class="page-info">...</span>`;

            for (let i = startPage; i <= endPage; i++) {{
                html += `<button onclick="goToPage(${{i}})" class="${{i === currentPage ? 'active' : ''}}">${{i}}</button>`;
            }}

            if (endPage < totalPages) html += `<span class="page-info">...</span><button onclick="goToPage(${{totalPages}})">${{totalPages}}</button>`;

            html += `<button onclick="goToPage(${{currentPage + 1}})" ${{currentPage === totalPages ? 'disabled' : ''}}">Next &gt;</button>`;

            container.innerHTML = html;
        }}

        function goToPage(page) {{
            currentPage = page;
            renderPage();
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function setFilter(filter) {{
            currentFilter = filter;
            currentPage = 1;

            document.querySelectorAll('.filter-tab').forEach(t => {{
                t.classList.remove('active');
                t.setAttribute('aria-pressed', 'false');
            }});
            const activeTab = document.querySelector(`[data-filter="${{filter}}"]`);
            activeTab.classList.add('active');
            activeTab.setAttribute('aria-pressed', 'true');

            renderPage();
        }}

        document.querySelectorAll('.filter-tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                const filter = tab.dataset.filter;
                setFilter(filter);
                history.pushState(null, '', filter === 'all' ? './' : filter);
            }});
        }});

        // URL 경로에 따라 초기 필터 설정
        const path = location.pathname.split('/').pop();
        if (path === 'market' || path === 'dev') {{
            currentFilter = path;
            document.querySelectorAll('.filter-tab').forEach(t => {{
                t.classList.remove('active');
                t.setAttribute('aria-pressed', 'false');
            }});
            document.querySelector(`[data-filter="${{path}}"]`).classList.add('active');
            document.querySelector(`[data-filter="${{path}}"]`).setAttribute('aria-pressed', 'true');
        }}

        renderPage();
    </script>
</body>
</html>'''

        self.index_file.write_text(html_content, encoding='utf-8')

        # market.html, dev.html 생성 (같은 내용, URL 라우팅용)
        (self.docs_dir / "market.html").write_text(html_content, encoding='utf-8')
        (self.docs_dir / "dev.html").write_text(html_content, encoding='utf-8')

        print(f"[Publisher] 인덱스 업데이트: {self.index_file}")

    def _generate_sitemap(self, reports: list):
        """sitemap.xml 생성"""
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        today = now.strftime("%Y-%m-%d")

        urls = [
            f'''  <url>
    <loc>{self.SITE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>''',
            f'''  <url>
    <loc>{self.SITE_URL}/market</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>''',
            f'''  <url>
    <loc>{self.SITE_URL}/dev</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>'''
        ]

        for r in reports[:30]:  # 최근 30개 리포트
            report_url = f"{self.SITE_URL}/reports/{r['filename']}"
            urls.append(f'''  <url>
    <loc>{report_url}</loc>
    <lastmod>{r['date']}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>''')

        sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''

        self.sitemap_file.write_text(sitemap, encoding='utf-8')
        print(f"[Publisher] Sitemap 업데이트: {self.sitemap_file}")

    def _generate_robots(self):
        """robots.txt 생성"""
        if self.robots_file.exists():
            return

        robots = f'''# Trend Reporter - robots.txt
# https://wj2kim.github.io/trend-reporter/

User-agent: *
Allow: /

# Sitemap
Sitemap: {self.SITE_URL}/sitemap.xml

# Crawl-delay (optional, for polite crawlers)
Crawl-delay: 1
'''
        self.robots_file.write_text(robots, encoding='utf-8')
        print(f"[Publisher] robots.txt 생성: {self.robots_file}")

    def _generate_feed(self, reports: list):
        """RSS 2.0 피드 생성"""
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        pub_date = now.strftime("%a, %d %b %Y %H:%M:%S +0900")

        items = []
        for r in reports[:20]:  # 최근 20개
            report_url = f"{self.SITE_URL}/reports/{r['filename']}"
            # RFC 822 날짜 형식
            item_date = f"{r['date']}T{r['time']}:00+09:00"
            try:
                dt = datetime.fromisoformat(item_date.replace('+09:00', ''))
                dt = kst.localize(dt)
                rfc_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0900")
            except:
                rfc_date = pub_date

            description = r.get('description', '')
            category_label = "Market" if r.get('category') == 'market' else "Dev"
            reading_time = r.get('reading_time', 1)

            items.append(f'''    <item>
      <title><![CDATA[{r['title']}]]></title>
      <link>{report_url}</link>
      <guid isPermaLink="true">{report_url}</guid>
      <pubDate>{rfc_date}</pubDate>
      <category>{category_label}</category>
      <description><![CDATA[{description} (읽기 시간: {reading_time}분)]]></description>
    </item>''')

        feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{self.SITE_NAME}</title>
    <description>{self.SITE_DESCRIPTION}</description>
    <link>{self.SITE_URL}/</link>
    <atom:link href="{self.SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>{self.SITE_LANGUAGE}</language>
    <lastBuildDate>{pub_date}</lastBuildDate>
    <pubDate>{pub_date}</pubDate>
    <ttl>60</ttl>
    <image>
      <url>{self.SITE_LOGO}</url>
      <title>{self.SITE_NAME}</title>
      <link>{self.SITE_URL}/</link>
    </image>
{chr(10).join(items)}
  </channel>
</rss>'''

        self.feed_file.write_text(feed, encoding='utf-8')
        print(f"[Publisher] RSS Feed 업데이트: {self.feed_file}")
