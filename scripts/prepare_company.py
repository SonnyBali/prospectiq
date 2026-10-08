"""Prepare public-company Google research, then optionally mint approved private pages.

This incurs one Vertex research call and one OpenAI intelligence call per page.
Admin/provider credentials remain server-side/in-memory Secret Manager values.
Evidence and private links go only to an ignored artifacts file; stdout contains
counts/opaque IDs, never tokens, recipient email/phone, or provider response text.
No HighLevel record, message, enrollment, voice call or calendar is changed.
"""
import argparse
import json
from pathlib import Path

import httpx

from app.integrations import SecretStore, VertexResearch

ORIGIN = 'https://prospect.firewireads.com'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--company', required=True)
    parser.add_argument('--website', required=True)
    parser.add_argument('--industry', required=True)
    parser.add_argument('--first-name', action='append', default=[])
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--evidence-file', default='artifacts/company-research.json')
    parser.add_argument('--links-file', default='artifacts/private-client-links.json')
    args = parser.parse_args()
    evidence_path = Path(args.evidence_file)
    links_path = Path(args.links_file)
    for path in (evidence_path, links_path):
        if path.resolve().parent != Path('artifacts').resolve():
            raise ValueError('Evidence/private output must stay in ignored artifacts directory')
    if evidence_path.exists():
        saved = json.loads(evidence_path.read_text(encoding='utf-8'))
        if saved['company'] != args.company or saved['website'] != args.website:
            raise ValueError('Cached company research identity mismatch')
        evidence = saved['evidence']
        reused = True
    else:
        evidence = VertexResearch('ai-leadscore', 'us-central1', 'gemini-2.5-flash').research(args.company, args.website)
        evidence_path.parent.mkdir(exist_ok=True)
        evidence_path.write_text(json.dumps({'company': args.company, 'website': args.website,
                                            'evidence': evidence}, indent=2), encoding='utf-8')
        reused = False
    print(json.dumps({'research_prepared': True, 'sources': len(evidence['sources']),
                      'google_attribution': bool(evidence.get('search_suggestions_html')), 'research_reused': reused}))
    if not args.publish:
        return
    if not args.first_name or links_path.exists():
        raise ValueError('Named pages required; reconcile existing private-link file before republishing')
    key = SecretStore('ai-leadscore').get('PROSPECTIQ_ADMIN_KEY')
    records = []
    with httpx.Client(base_url=ORIGIN, follow_redirects=False, timeout=90) as client:
        for first_name in args.first_name:
            response = client.post('/api/admin/prospects/import', headers={'X-Admin-Key': key}, json={
                'first_name': first_name, 'company_name': args.company, 'industry': args.industry,
                'website': args.website, 'synthetic': False, 'sources': evidence['sources'],
                'research_notes': evidence['notes'],
                'research_attribution_html': evidence.get('search_suggestions_html', ''),
            })
            if response.status_code != 200:
                raise RuntimeError(f'Intelligence/access not verified: HTTP {response.status_code}; no provider body logged')
            record = response.json()
            record['first_name'] = first_name
            records.append(record)
            # Save each success immediately so a later failure does not lose issued links.
            links_path.write_text(json.dumps({'company': args.company, 'pages': records}, indent=2), encoding='utf-8')
            print(json.dumps({'page_ready': True, 'prospect_id': record['prospect_id'],
                              'request_id': response.headers.get('x-request-id'), 'crm_linked': False,
                              'outreach_sent': False}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'not_verified', 'error_type': type(error).__name__,
                          'diagnostics': 'omitted; reconcile saved artifacts before retry'}))
        raise SystemExit(1) from None
