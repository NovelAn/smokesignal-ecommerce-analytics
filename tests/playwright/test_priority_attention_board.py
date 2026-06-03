"""
Playwright test for PriorityAttentionBoard component
Tests: pagination, filtering, table display, export button
"""
from playwright.sync_api import sync_playwright
import time

def test_priority_attention_board():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture console logs
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

        # Wait a bit for the page to fully render
        time.sleep(3)

        # Print console messages for debugging
        print("\n[DEBUG] Console messages:")
        for msg in console_messages:
            if 'error' in msg.lower() or 'warn' in msg.lower():
                print(f"  {msg}")

        print("[INFO] Navigating to http://localhost:3003...")
        page.goto('http://localhost:3003')
        page.wait_for_load_state('networkidle')

        # Take initial screenshot
        page.screenshot(path='test_screenshots/01_initial_load.png', full_page=True)
        print("[OK] Screenshot saved: 01_initial_load.png")

        # Check if PriorityAttentionBoard is visible
        print("\n[INFO] Checking PriorityAttentionBoard component...")

        # Look for the title "需优先跟进的客户"
        title_locator = page.locator('text=需优先跟进的客户')
        if title_locator.count() > 0:
            print("[OK] Title found: 需优先跟进的客户")
        else:
            print("[FAIL] Title not found")

        # Check for filter button
        filter_btn = page.locator('button:has-text("筛选")')
        if filter_btn.count() > 0:
            print("[OK] Filter button found")
            filter_btn.first.click()
            time.sleep(0.5)
            page.screenshot(path='test_screenshots/02_filter_panel_open.png', full_page=True)
            print("[OK] Screenshot saved: 02_filter_panel_open.png")
        else:
            print("[FAIL] Filter button not found")

        # Check for export button
        export_btn = page.locator('button:has-text("导出 CSV")')
        if export_btn.count() > 0:
            print("[OK] Export CSV button found")
        else:
            print("[FAIL] Export CSV button not found")

        # Check for table headers
        expected_headers = ['客户', '优先级', '情感', '意图', 'RFM', 'L6M', 'L1Y', '退款率', '最后购买', 'AI建议']
        print("\n[INFO] Checking table headers...")
        for header in expected_headers:
            header_locator = page.locator(f'th:has-text("{header}")')
            if header_locator.count() > 0:
                print(f"  [OK] Header found: {header}")
            else:
                print(f"  [FAIL] Header missing: {header}")

        # Check for table rows
        rows = page.locator('tbody tr')
        row_count = rows.count()
        print(f"\n[INFO] Table rows found: {row_count}")
        if row_count > 0:
            print("[OK] Table has data rows")
        else:
            print("[WARN] No data rows (might be empty or loading)")

        # Test pagination if available (in header area)
        print("\n[INFO] Testing pagination...")
        # Check for pagination in the header (chevron buttons)
        next_btn = page.locator('button[title="下一页"]')
        prev_btn = page.locator('button[title="上一页"]')

        if next_btn.count() > 0 and not next_btn.first.is_disabled():
            print("[OK] Next page button found in header")
            next_btn.first.click()
            time.sleep(1)
            page.screenshot(path='test_screenshots/03_page2.png', full_page=True)
            print("[OK] Screenshot saved: 03_page2.png")

            # Go back to first page
            if prev_btn.count() > 0 and not prev_btn.first.is_disabled():
                prev_btn.first.click()
                time.sleep(1)
                print("[OK] Returned to first page")
        else:
            # Alternative: check for page number indicator
            page_indicator = page.locator('text=/1\\s*/\\s*\\d+/')
            if page_indicator.count() > 0:
                print(f"[OK] Page indicator found: {page_indicator.first.text_content()}")
            else:
                print("[WARN] Pagination not visible or only one page")

        # Check for customer count (new format: "X 位")
        count_locator = page.locator('text=/\\d+\\s*位/')
        if count_locator.count() > 0:
            count_text = count_locator.first.text_content()
            print(f"\n[INFO] Customer count: {count_text}")
        else:
            print("[WARN] Customer count not found")

        # Final screenshot
        page.screenshot(path='test_screenshots/04_final.png', full_page=True)
        print("[OK] Screenshot saved: 04_final.png")

        print("\n[DONE] Test completed!")
        browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('test_screenshots', exist_ok=True)
    test_priority_attention_board()
