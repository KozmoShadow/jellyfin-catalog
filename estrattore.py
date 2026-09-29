from playwright.sync_api import sync_playwright

def estrai_flussi(url_pagina):
    video_link_1080 = None
    video_link_720 = None
    audio_link = None

    def handle_response(response):
        nonlocal video_link_1080, video_link_720, audio_link
        url = response.url
        if "type=video" in url and "rendition=1080" in url:
            video_link_1080 = url
        elif "type=video" in url and "rendition=720" in url:
            video_link_720 = url
        elif "type=audio&rendition" in url:
            audio_link = url

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("response", handle_response)
        
        page.goto(url_pagina)
        page.wait_for_timeout(10)
        
        try:
            frame = page.frame_locator("iframe").first
            
            settings_btn = frame.get_by_role("button", name="Settings")
            settings_btn.wait_for(state="visible", timeout=0)
            settings_btn.click()
            
            page.wait_for_timeout(10)
            
            quality_btn = frame.locator("[aria-label='1080p']")
            quality_btn.wait_for(state="visible", timeout=10)
            quality_btn.click()
            
        except Exception:
            pass
        
        page.wait_for_timeout(200)
        browser.close()

    final_video = video_link_1080 if video_link_1080 else video_link_720
    return final_video, audio_link