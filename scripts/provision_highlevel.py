"""Create only ProspectIQ's dedicated FireWire contact field and native trigger link.

Credentials stay in Secret Manager/in memory. No contacts, messages, enrollments,
or existing workflows are changed. Unknown write outcomes require reconciliation.
"""
import json
import time

import httpx

from app.config import Settings
from app.integrations import HighLevelClient, SecretStore


def main():
    settings = Settings.from_env()
    store = SecretStore(settings.project)
    location = store.get(settings.ghl_location_secret)
    if location != settings.ghl_location or location != 'aFnKcmUdTSPIjo7lCaix':
        raise RuntimeError('FireWire tenant mismatch')
    token = store.get(settings.ghl_secret)
    with httpx.Client(follow_redirects=False) as transport:
        response = transport.get(f'{HighLevelClient.API}/locations/{location}',
                                 headers={'Authorization': f'Bearer {token}', 'Version': '2021-07-28'}, timeout=20)
        if response.status_code != 200:
            raise RuntimeError('FireWire tenant verification unavailable')
        current = response.json().get('location', {})
        if current.get('id') != location or current.get('name') != 'FireWireAds.com':
            raise RuntimeError('FireWire tenant identity mismatch')
        client = HighLevelClient(token, location, client=transport)
        try:
            field = client.ensure_dashboard_field()
            link = client.ensure_dashboard_trigger_link()
        except Exception as error:
            # IntegrationUnavailable contains only fixed application diagnostics.
            from app.integrations import IntegrationUnavailable
            if isinstance(error, IntegrationUnavailable):
                print(json.dumps({'phase': 'field_or_trigger_verification', 'diagnostic': str(error)}))
            raise
        tag_records = []
        tags_url = f'{HighLevelClient.API}/locations/{location}/tags'
        headers = {'Authorization': f'Bearer {token}', 'Version': '2021-07-28'}
        for name in ('prospectiq-approved', 'prospectiq-feedback-approved', 'prospectiq-feedback-sent', 'Spanish'):
            before = transport.get(tags_url, headers=headers, timeout=20)
            if before.status_code != 200:
                raise RuntimeError('Tag inventory unavailable')
            matches = [tag for tag in before.json().get('tags', []) if str(tag.get('name', '')).casefold() == name.casefold()]
            if len(matches) > 1:
                raise RuntimeError('Dedicated approval tag is ambiguous')
            if not matches:
                created = transport.post(tags_url, headers=headers, json={'name': name}, timeout=20)
                if created.status_code not in (200, 201):
                    raise RuntimeError('Tag creation unverified; reconcile before retry')
            # Newly created tags can lag in the provider's read index. Retry only
            # reads; an uncertain create is never submitted a second time.
            for attempt in range(3):
                after = transport.get(tags_url, headers=headers, timeout=20)
                if after.status_code != 200:
                    raise RuntimeError('Tag readback unavailable')
                verified = [tag for tag in after.json().get('tags', []) if str(tag.get('name', '')).casefold() == name.casefold()]
                if verified:
                    break
                if attempt < 2:
                    time.sleep(1)
            if len(verified) != 1 or verified[0].get('locationId') != location or not verified[0].get('id'):
                raise RuntimeError('Tag identity/tenant readback failed')
            tag_records.append({'name': name, 'id': verified[0]['id']})
        print(json.dumps({'tenant_verified': True, 'field_id': field['id'],
                          'field_key': field['fieldKey'], 'trigger_link_id': link['id'],
                          'trigger_link_merge': link['fieldKey'],
                          'destination': link['redirectTo'], 'tags': tag_records, 'outreach_sent': False}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'not_verified', 'error_type': type(error).__name__,
                          'outreach_sent': False, 'action': 'reconcile dedicated field/link before retry'}))
        raise SystemExit(1) from None
