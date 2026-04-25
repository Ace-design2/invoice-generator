from playwright.sync_api import sync_playwright

html = """
<!DOCTYPE html>
<html lang="en">
<head>
<style>
    body { font-family: sans-serif; margin: 0; padding: 0; }
    .print-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        padding: 0 64px 20px 64px;
        box-sizing: border-box;
    }
</style>
</head>
<body>
<table style="width: 100%; border-collapse: collapse;">
    <thead>
        <tr><td style="padding: 40px 64px 0 64px;"><h1>Invoice</h1><hr></td></tr>
    </thead>
    <tbody>
"""
for i in range(10):
    html += f'<tr><td style="padding: 10px 64px; border-bottom: 1px solid #ccc;">Item {i+1}</td></tr>\n'

html += """
        <tr><td style="padding: 20px 64px;"><h2>Total: $1000</h2></td></tr>
    </tbody>
    <tfoot>
        <tr><td><div style="height: 120px;"></div></td></tr>
    </tfoot>
</table>

<div class="print-footer">
    <div style="border-top: 1px dashed black; padding-top: 8px;">
        <b>REFUND POLICY</b><br>
        <i>All sales are final. We do not accept returns.</i>
    </div>
</div>
</body>
</html>
"""

footer = '<div style="text-align: right; width: 100%; font-size: 10px; padding: 0 64px; font-family: sans-serif;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html)
    page.pdf(path="test_table.pdf", format="A4", display_header_footer=True, footer_template=footer, margin={"top": "0px", "bottom": "40px", "left": "0px", "right": "0px"})
    browser.close()
