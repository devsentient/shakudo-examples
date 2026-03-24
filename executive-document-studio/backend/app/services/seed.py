from __future__ import annotations

from datetime import datetime

from app.services import database
from app.services.embedding_service import embedding_service

DOCUMENTS = [
    {
        'id': 'doc_annual_2023',
        'title': 'Annual Report 2023',
        'type': 'annual_report',
        'tags': ['finance', 'strategy', 'board'],
        'date': '2023-12-31',
        'summary': 'Financial performance, capital priorities, and strategic themes entering 2024.',
        'content': 'George Weston Limited delivered resilient food retail performance in 2023 with continued focus on margin discipline, premium category growth, and supply chain modernization. Leadership highlighted disciplined capital allocation and measured appetite for adjacent acquisitions where integration complexity remains manageable.',
    },
    {
        'id': 'doc_shoppers_case',
        'title': 'Acquisition Case Study — Shoppers Integration Learnings',
        'type': 'acquisition_case_study',
        'tags': ['acquisition', 'integration', 'board'],
        'date': '2022-09-20',
        'summary': 'Lessons learned on integration sequencing, governance, and synergy capture.',
        'content': 'Historical review of the Shoppers integration emphasizes the value of early executive sponsorship, clear integration milestones, and conservative synergy assumptions. The strongest outcomes came when leadership aligned the operating model before pursuing accelerated commercial integration.',
    },
    {
        'id': 'doc_market_2024',
        'title': 'Canadian Grocery Retail Landscape 2024',
        'type': 'market_analysis',
        'tags': ['market', 'competition', 'consumer'],
        'date': '2024-06-30',
        'summary': 'Competitive intensity, premium category expansion, and consumer shifts.',
        'content': 'The premium and organic grocery segment continues to outgrow conventional categories in urban and affluent suburban trade areas. Competitive dynamics suggest acquisitions can accelerate share capture when paired with localized assortment, omnichannel convenience, and a disciplined brand migration strategy.',
    },
    {
        'id': 'doc_strategy_2025',
        'title': 'Strategic Plan 2025',
        'type': 'strategic_plan',
        'tags': ['strategy', 'growth', 'executive'],
        'date': '2025-01-15',
        'summary': 'Leadership growth priorities and portfolio management focus areas.',
        'content': 'The 2025 strategic plan prioritizes premium food categories, platform efficiency, and selective inorganic growth where management confidence in execution is high. Proposed transactions should strengthen category exposure without compromising margin quality or leadership focus.',
    },
    {
        'id': 'doc_esg_2023',
        'title': 'ESG Report 2023',
        'type': 'esg_report',
        'tags': ['esg', 'supply chain', 'governance'],
        'date': '2023-11-01',
        'summary': 'Supply chain resilience, governance commitments, and sustainability posture.',
        'content': 'Governance committees continue to prioritize transparent sourcing, resilient logistics partnerships, and measurable environmental targets. Any acquisition in food retail should be reviewed for supplier transparency, packaging exposure, and governance maturity before recommendation to the board.',
    },
    {
        'id': 'doc_board_template',
        'title': 'Board Memo Template — M&A Review',
        'type': 'board_presentation',
        'tags': ['board', 'memo', 'template'],
        'date': '2024-10-01',
        'summary': 'Standard board communication format for acquisition decisions.',
        'content': 'Board communication should begin with a concise executive summary, followed by strategic rationale, financial framing, risks, and a clear recommendation. The strongest memos ground each claim in precedent and highlight where management is exercising conservatism in assumptions.',
    },
]

TEMPLATES = [
    {
        'id': 'template_board_memo',
        'name': 'Board Memo',
        'description': 'Board-ready acquisition evaluation with grounded recommendations and explicit risk framing.',
        'sections': [
            {'id': 'executive_summary', 'title': 'Executive Summary', 'instructions': 'Two to three paragraphs, direct and board-ready.'},
            {'id': 'background', 'title': 'Background', 'instructions': 'Summarize the context, strategic setting, and relevant precedent.'},
            {'id': 'analysis', 'title': 'Analysis', 'instructions': 'Explain the commercial, strategic, and operating implications.'},
            {'id': 'recommendation', 'title': 'Recommendation', 'instructions': 'Provide a crisp recommendation with gated next steps.'},
            {'id': 'risk_assessment', 'title': 'Risk Assessment', 'instructions': 'Present conservative risks and proposed mitigations.'},
        ],
        'system_prompt': 'You are an executive communication assistant producing board-ready acquisition memos.',
    },
    {
        'id': 'template_strategic_brief',
        'name': 'Strategic Brief',
        'description': 'A compact executive brief for leadership alignment and directional decisions.',
        'sections': [
            {'id': 'situation', 'title': 'Situation', 'instructions': 'Explain the situation succinctly.'},
            {'id': 'implications', 'title': 'Implications', 'instructions': 'Surface why it matters now.'},
            {'id': 'actions', 'title': 'Recommended Actions', 'instructions': 'Lay out the path forward.'},
        ],
        'system_prompt': 'You are an executive strategy assistant producing concise leadership briefs.',
    },
]


async def seed_demo_data() -> None:
    existing = await database.fetch_one('SELECT COUNT(*) AS count FROM documents')
    if existing and int(existing['count']) > 0:
        return

    now = datetime.utcnow().isoformat()
    await database.insert_many(
        'INSERT INTO documents (id, title, type, tags, date, summary, content, source_name, source_kind, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            (
                item['id'],
                item['title'],
                item['type'],
                database.dumps(item['tags']),
                item['date'],
                item['summary'],
                item['content'],
                item['title'],
                'seed',
                now,
                now,
            )
            for item in DOCUMENTS
        ],
    )

    chunk_rows = []
    for item in DOCUMENTS:
        paragraphs = [segment.strip() for segment in item['content'].split('. ') if segment.strip()]
        for index, paragraph in enumerate(paragraphs, start=1):
            text = paragraph if paragraph.endswith('.') else f'{paragraph}.'
            chunk_rows.append(
                (
                    f"{item['id']}_chunk_{index:02d}",
                    item['id'],
                    item['title'],
                    text,
                    index,
                    database.dumps({'section': f'part_{index}', 'order': index}),
                    None,
                )
            )
    await database.insert_many(
        'INSERT INTO chunks (id, document_id, document_title, text, position, metadata, embedding) VALUES (?, ?, ?, ?, ?, ?, ?)',
        chunk_rows,
    )

    await database.insert_many(
        'INSERT INTO templates (id, name, description, sections, system_prompt) VALUES (?, ?, ?, ?, ?)',
        [
            (
                item['id'],
                item['name'],
                item['description'],
                database.dumps(item['sections']),
                item['system_prompt'],
            )
            for item in TEMPLATES
        ],
    )

    await embedding_service.reindex_all()
