"""Verify the live server offers zero-count conflict review and can confirm it."""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def run():
    port = sys.argv[1] if len(sys.argv) > 1 else '8050'
    blank_review = '--blanks' in sys.argv
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1400, 'height': 1000})
        page.goto(f'http://127.0.0.1:{port}')
        page.get_by_role('tab', name='Data', exact=True).click()
        data = b'Disease,Year,Week,Cases\nDengue,2024,52,2\nDengue,2024,53,0\nMeasles-Rubella,2024,52,1\nMeasles-Rubella,2024,53,5'
        if blank_review:
            data = ('Disease,Year,Week,Cases\n' + '\n'.join(f'Dengue,{y},{w},{n}'
                    for y in [2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024]
                    for w, n in [(52, '2'), (53, '')])).encode()
        page.locator('#w-upload input[type=file]').set_input_files({
            'name': 'week53-confirmation.csv', 'mimeType': 'text/csv',
            'buffer': data})
        expect(page.get_by_role('dialog')).to_be_visible()
        page.locator('#w-fact-panel').evaluate("el => { el.open = true; }")
        if blank_review:
            page.evaluate("""() => {
                window.dash_clientside.set_props({type:'w-fact',field:'group_resolution:Dengue~53~week53-absent'}, {value:'zero'});
                window.dash_clientside.set_props({type:'w-fact',field:'group_evidence:Dengue~53~week53-absent'}, {value:'Synthetic test: zero confirmed'});
            }""")
            page.locator('#w-activate').click()
            expect(page.locator('#w-review-message')).to_contain_text('saved in this review')
            expect(page.locator('#w-activate')).to_be_disabled()
            expect(page.locator('#w-page-title')).to_have_text('Data')
            page.locator('#w-fact-panel').evaluate('el => {el.open = false}')
            page.get_by_role('link', name='Resolve Dengue week 53 entries', exact=True).click()
            expect(page.locator('#w-fact-panel')).to_have_attribute('open', '')
        group = page.locator('#w-facts details').filter(has=page.locator('summary').filter(has_text='Week 53 reported'))
        group.evaluate('el => {el.open = true}')
        expect(group).to_contain_text('Dengue')
        if not blank_review:
            expect(group).to_contain_text('Measles-Rubella')
        inputs = group.locator('input[type=text]')
        # Select each review choice through Dash props in this isolated test page.
        controls = group.locator('[id]').evaluate_all("els => els.map(el => {try{return JSON.parse(el.id)}catch{return null}}).filter(id => id?.field?.startsWith('conflict:'))")
        assert len(controls) == (8 if blank_review else 2), controls
        for identity in controls:
            page.evaluate("id => window.dash_clientside.set_props(id, {value:'exclude'})", identity)
        for i in range(inputs.count()):
            inputs.nth(i).fill('Synthetic browser test: source review confirms nonexistent week')
        page.locator('#w-apply-facts').click()
        expect(page.locator('#w-activate')).to_be_enabled()
        page.locator('#w-activate').click()
        expect(page.get_by_role('dialog')).not_to_be_visible()
        active = page.evaluate("JSON.parse(sessionStorage.getItem('w-active'))")
        assert len(active['records']) == (8 if blank_review else 2)
        assert all(r['morbidity_week'] == 52 for r in active['records'])
        target = Path('evidence/week53-confirmation')
        target.mkdir(exist_ok=True)
        page.screenshot(path=str(target / f'confirmed-{port}.png'))
        print(json.dumps({'port': port, 'confirmed': True, 'records': len(active['records'])}))
        browser.close()


if __name__ == '__main__':
    run()
