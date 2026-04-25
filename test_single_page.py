from playwright.sync_api import sync_playwright

html = "<html><body><h1>Hello World</h1></body></html>"
footer = """
<div style="font-size: 10px; padding: 0 64px; width: 100%;">
    <b>REFUND POLICY</b><br>All sales are final.
    <div style="text-align:right">Page <span class="pageNumber"></span></div>
</div>
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html)
    page.pdf(path="test_single_page.pdf", format="A4", display_header_footer=True, header_template="<div></div>", footer_template=footer, margin={"top": "40px", "bottom": "130px", "left": "0px", "right": "0px"})
    browser.close()
