from playwright.sync_api import sync_playwright

html = """
<!DOCTYPE html>
<html>
<head>
<style>
    body { font-family: sans-serif; margin: 0; }
    .container { padding: 0 64px; }
    .item { height: 40px; border-bottom: 1px solid #ccc; display: flex; align-items: center; }
</style>
</head>
<body>
<div class="container">
    <h1>Invoice</h1>
    <div style="height: 100px; background: #eee; margin-bottom: 20px;">Customer Details</div>
"""
for i in range(40):
    html += f'<div class="item">Item {i+1}</div>\n'

html += """
    <div style="height: 100px; background: #ddd; margin-top: 20px;">Bank Details</div>
</div>
</body>
</html>
"""

footer = """
<div style="font-family: sans-serif; font-size: 10px; color: black; padding: 0 64px; width: 100%; box-sizing: border-box;">
    <div style="border-top: 1px solid #000; padding-top: 4px;">
        <b>REFUND POLICY</b><br>
        <i>Refunds are accepted within 7 days. Items must be in original condition.</i>
    </div>
    <div style="text-align: right; width: 100%;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>
</div>
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html)
    page.pdf(path="test_playwright.pdf", format="A4", display_header_footer=True, header_template="<div></div>", footer_template=footer, margin={"top": "40px", "bottom": "120px", "left": "0", "right": "0"})
    browser.close()
