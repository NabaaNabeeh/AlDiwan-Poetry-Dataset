import os
import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup

# ── Configuration ─────────────────────────────────────────────────────────────
POETS_CSV_PATH = "poets_clean.csv"   # input: your poets file
OUTPUT_CSV     = "all_poems.csv"     # output: all poems
DELAY          = 0.8                 # seconds between poem requests
FEED_DELAY     = 0.8                 # seconds between feed API pages
COOLDOWN_EVERY = 50                  # extra pause every N poems per poet
COOLDOWN_SECS  = 8                   # seconds for the cooldown pause
MAX_RETRIES    = 3                   # retry attempts on connection error
# ──────────────────────────────────────────────────────────────────────────────

BASE_URL = "https://www.aldiwan.net"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
}


def get_poem_links(poet_id):
    """
    Get ALL poem URLs for a poet using the paginated poems-feed API.
    Follows next_cursor pagination until all pages are exhausted.
    """
    links, cursor = [], None
    feed_url = f"{BASE_URL}/cat-{poet_id}/poems-feed"

    while True:
        try:
            url = f"{feed_url}?cursor={cursor}" if cursor else feed_url
            r = requests.get(url, headers=HEADERS, timeout=15)
            data = r.json()
            html = data.get("html", "")
            if not html:
                break
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if re.search(r"poem\d+\.html", href):
                    full = href if href.startswith("http") else BASE_URL + "/" + href.lstrip("/")
                    if full not in links:
                        links.append(full)
            cursor = data.get("next_cursor")
            if not cursor:
                break
            time.sleep(FEED_DELAY)
        except Exception as e:
            print(f"  Error getting poem links: {e}")
            break

    return links


def scrape_poem(poem_url, poet_id, poet_name, era):
   
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(poem_url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                return None
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            # poem id from url e.g. poem160256.html → 160256
            poem_id = re.search(r"poem(\d+)", poem_url)
            poem_id = poem_id.group(1) if poem_id else ""

            # title: from <title> tag, first part before " - "
            title = ""
            t = soup.find("title")
            if t:
                title = t.get_text(strip=True).split(" - ")[0].strip()

            # full poem text — handle all structures
            poem_text = ""
            poem_content_div = soup.find(id="poem_content")

            # Structure 1: free verse — <h4 id="poem_content"> with <br> tags
            if poem_content_div and poem_content_div.name == "h4":
                for br in poem_content_div.find_all("br"):
                    br.replace_with("\n")
                poem_text = poem_content_div.get_text(strip=True)

            # Structure 2 & 3: classical verse — <h3> pairs inside poem_content div
            elif poem_content_div:
                h3_tags = []
                for tag in poem_content_div.find_all("h3"):
                    text = tag.get_text(strip=True)
                    if "تم اضافة" in text or "أضف معلومة" in text or "المساهمات" in text:
                        break
                    if text:
                        h3_tags.append(tag)
                verses = []
                for i in range(0, len(h3_tags) - 1, 2):
                    h1 = h3_tags[i].get_text(strip=True)
                    h2 = h3_tags[i + 1].get_text(strip=True)
                    if h1 and h2:
                        verses.append(f"{h1} *** {h2}")
                poem_text = "\n".join(verses)

            # Structure 4: fallback — <h3> pairs anywhere on page
            if not poem_text:
                h3_tags = []
                for tag in soup.find_all("h3"):
                    text = tag.get_text(strip=True)
                    if "تم اضافة" in text or "أضف معلومة" in text or "المساهمات" in text:
                        break
                    if text:
                        h3_tags.append(tag)
                verses = []
                for i in range(0, len(h3_tags) - 1, 2):
                    h1 = h3_tags[i].get_text(strip=True)
                    h2 = h3_tags[i + 1].get_text(strip=True)
                    if h1 and h2:
                        verses.append(f"{h1} *** {h2}")
                poem_text = "\n".join(verses)

            # metadata: theme from links
            theme = ""
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if "Poems-Topics-" in href and not theme:
                    theme = text
              

            # verse count from page text
            verses_count = ""
            m = re.search(r"عدد الأبيات[:\s]*(\d+)", soup.get_text())
            if m:
                verses_count = m.group(1)

            return {
                "poem_id"     : poem_id,
                "poet_id"     : poet_id,
                "title"       : title,
                "full_text"   : poem_text,
                "poet_name"   : poet_name,
                "era"         : era,
                "theme"       : theme,
                "verses_count": verses_count,
                "source_url"  : poem_url,
            }

        except Exception as e:
            if attempt < MAX_RETRIES:
                wait = 5 * attempt
                print(f"  Retry {attempt}/{MAX_RETRIES} for {poem_url} after {wait}s: {e}")
                time.sleep(wait)
            else:
                print(f"  Failed after {MAX_RETRIES} attempts: {poem_url}: {e}")
                return None


def scrape_all_poems():
    # load all poets
    try:
        poets_df = pd.read_csv(POETS_CSV_PATH, encoding="utf-8-sig")
    except Exception:
        poets_df = pd.read_excel(POETS_CSV_PATH)

    print(f"Loaded {len(poets_df)} poets from '{POETS_CSV_PATH}'")

    # resume: load already-scraped URLs
    seen_urls = set()
    if os.path.exists(OUTPUT_CSV):
        existing = pd.read_csv(OUTPUT_CSV, encoding="utf-8-sig")
        seen_urls = set(existing["source_url"].dropna().tolist())
        print(f"Resuming — {len(seen_urls)} poems already scraped\n")
    else:
        print("Starting fresh\n")

    all_poems    = []
    total_poets  = len(poets_df)

    for idx, row in poets_df.iterrows():
        poet_id   = row.get("poet_id", "")
        poet_name = row.get("name", "")
        poet_url  = row.get("source_url", "")
        era       = row.get("era", "")

        if not poet_id or pd.isna(poet_id):
            continue
        if not poet_url or pd.isna(poet_url):
            continue

        print(f"[{idx+1}/{total_poets}] {poet_name}")

        poem_links = get_poem_links(int(poet_id))
        new_links  = [l for l in poem_links if l not in seen_urls]
        print(f"  {len(poem_links)} total poems, {len(new_links)} new")

        poems_this_poet = 0
        for p_url in new_links:
            poem = scrape_poem(p_url, poet_id, poet_name, era)
            if poem:
                all_poems.append(poem)
                seen_urls.add(p_url)
            time.sleep(DELAY)

            poems_this_poet += 1
            # cooldown every N poems to avoid rate limiting
            if poems_this_poet % COOLDOWN_EVERY == 0:
                print(f"  Cooldown after {poems_this_poet} poems...")
                time.sleep(COOLDOWN_SECS)

        # save after every poet
        if all_poems:
            df_new = pd.DataFrame(all_poems)
            if os.path.exists(OUTPUT_CSV):
                df_existing = pd.read_csv(OUTPUT_CSV, encoding="utf-8-sig")
                df_all = pd.concat([df_existing, df_new], ignore_index=True)
            else:
                df_all = df_new
            df_all.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
            all_poems = []
            print(f"  Saved — total so far: {len(seen_urls)} poems")

        time.sleep(DELAY)

    print(f"\nDone. Total poems scraped: {len(seen_urls)}")
    print(f"Saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    scrape_all_poems()
