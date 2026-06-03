"""
Playwright test for CSV export functionality
Tests: CSV export with Chinese characters (UTF-8 BOM)
"""
from playwright.sync_api import sync_playwright
import os
import time

def test_csv_export():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            accept_downloads=True  # Enable download handling
        )
        page = context.new_page()

        # Capture console logs
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

        print("[INFO] Navigating to http://localhost:3003...")
        page.goto('http://localhost:3003')

        # Wait for React to render
        print("[INFO] Waiting for page to load...")
        time.sleep(5)  # Give time for React to render

        # Take screenshot
        os.makedirs('test_screenshots', exist_ok=True)
        page.screenshot(path='test_screenshots/csv_01_loaded.png', full_page=True)
        print("[OK] Screenshot saved: csv_01_loaded.png")

        # Print console messages
        if console_messages:
            print("\n[INFO] Console messages:")
            for msg in console_messages:
                if 'error' in msg.lower():
                    print(f"  {msg}")

        # Look for the Priority Attention Board component
        print("\n[INFO] Looking for Priority Attention Board...")

        # Find the export CSV button - try different selectors
        selectors = [
            'button:has-text("导出")',
            'button:has-text("Export")',
            'button:has-text("CSV")',
            'text=需优先跟进的客户'  # Title of the component
        ]

        found = False
        for selector in selectors:
            count = page.locator(selector).count()
            if count > 0:
                print(f"[OK] Found {count} elements matching: {selector}")
                found = True
                break

        if not found:
            print("[WARN] Could not find Priority Attention Board with standard selectors")

            # List all buttons
            buttons = page.locator('button').all()
            print(f"\n[INFO] Found {len(buttons)} buttons on page:")
            for i, btn in enumerate(buttons[:20]):  # First 20 buttons
                try:
                    text = btn.text_content(timeout=1000)
                    if text and text.strip():
                        print(f"  {i+1}. {text[:60]}")
                except:
                    pass

        # Try to find and click export button
        export_btn = page.locator('button:has-text("导出")')
        if export_btn.count() == 0:
            export_btn = page.locator('button:has-text("Export")')

        if export_btn.count() > 0:
            print(f"\n[OK] Found Export CSV button ({export_btn.count()} matches)")

            # Setup download handler
            with page.expect_download(timeout=30000) as download_info:
                export_btn.first.click()

            download = download_info.value

            # Wait for download to complete
            download_path = os.path.join('test_screenshots', download.suggested_filename)
            download.save_as(download_path)
            print(f"[OK] Downloaded file: {download_path}")

            # Read and verify the file
            try:
                # Try different encodings
                content = None
                for encoding in ['utf-8-sig', 'utf-8', 'gbk']:
                    try:
                        with open(download_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        print(f"[OK] Successfully read file with {encoding} encoding")
                        break
                    except UnicodeDecodeError:
                        continue

                if content:
                    # Check for Chinese characters
                    chinese_headers = ['客户', '渠道', '买家类型', '优先级', '情感', '意图']
                    found_chinese = [h for h in chinese_headers if h in content]

                    if len(found_chinese) == len(chinese_headers):
                        print(f"[OK] All Chinese headers found: {found_chinese}")
                    else:
                        print(f"[WARN] Some Chinese headers missing. Found: {found_chinese}")

                    # Print first few lines
                    lines = content.split('\n')[:5]
                    print("\n[INFO] First 5 lines of CSV:")
                    for i, line in enumerate(lines):
                        print(f"  Line {i+1}: {line[:100]}...")

                    # Check file size
                    file_size = os.path.getsize(download_path)
                    print(f"\n[INFO] File size: {file_size} bytes")

                    # Check for BOM (first 3 bytes should be EF BB BF for UTF-8 BOM)
                    with open(download_path, 'rb') as f:
                        first_bytes = f.read(3)
                    if first_bytes == b'\xef\xbb\xbf':
                        print("[OK] UTF-8 BOM detected - Excel should display Chinese correctly!")
                    else:
                        print(f"[WARN] No UTF-8 BOM found. First bytes: {first_bytes.hex()}")

            except Exception as e:
                print(f"[FAIL] Failed to read file: {e}")

        else:
            print("[WARN] Export CSV button not found - checking if component exists...")

            # Check if the component title exists
            title = page.locator('text=需优先跟进的客户')
            if title.count() > 0:
                print("[OK] Priority Attention Board title found")
            else:
                print("[WARN] Priority Attention Board component not visible")

        # Take final screenshot
        page.screenshot(path='test_screenshots/csv_02_final.png', full_page=True)
        print("\n[OK] Screenshot saved: csv_02_final.png")

        print("\n[DONE] Test completed!")
        browser.close()

if __name__ == "__main__":
    test_csv_export()
