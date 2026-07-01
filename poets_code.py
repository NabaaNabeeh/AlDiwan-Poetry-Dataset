import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_URL = "https://www.aldiwan.net"
FEED_URL = f"{BASE_URL}/authers-feed"

headers_api  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
}
headers_html = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

ERAS = {
    "العصر الجاهلي"   : 7,
    "العصر الإسلامي"  : 25,
    "العصر الأموي"    : 28,
    "العصر العباسي"   : 27,
    "العصر الأندلسي"  : 26,
    "العصر الأيوبي"   : 30,
    "العصر المملوكي"  : 32,
    "العصر العثماني"  : 29,
    "عصر المخضرمون"   : 485,
}

SIMPLE_COUNTRIES = {
    "الإمارات"  : f"{BASE_URL}/cat-poets-uae",
    "الأردن"    : f"{BASE_URL}/cat-poets-jordan",
    "موريتانيا" : f"{BASE_URL}/cat-poets-mauritania",
    "البحرين"   : f"{BASE_URL}/cat-poets-bahrain",
    "السودان"   : f"{BASE_URL}/cat-poets-sudan",
    "عمان"      : f"{BASE_URL}/cat-poets-oman",
    "ليبيا"     : f"{BASE_URL}/cat-poets-libya",
    "الكويت"    : f"{BASE_URL}/cat-poets-kuwait",
    "الصومال"   : f"{BASE_URL}/cat-poets-Soomaaliya",
    "الجزائر"   : f"{BASE_URL}/cat-poets-algeria",
    "تونس"      : f"{BASE_URL}/cat-poets-tunisia",
    "قطر"       : f"{BASE_URL}/cat-poets-qatar",
    "السنغال"   : f"{BASE_URL}/cat-poets-Senegal",
}

API_COUNTRIES = {
    "المغرب"   : 35,
    "السعودية" : 34,
    "سوريا"    : 36,
    "لبنان"    : 37,
    "اليمن"    : 42,
    "العراق"   : 47,
    "فلسطين"   : 49,
    "مصر"      : 4,
}


def get_links_authers_feed(poet_type="all"):
    links, cursor = [], None
    while True:
        url = (f"{FEED_URL}?cursor={cursor}&type={poet_type}&id="
               if cursor else f"{FEED_URL}?type={poet_type}&id=")
        try:
            r = requests.get(url, headers=headers_api, timeout=15)
            data = r.json()
            html = data.get("html", "")
            if not html:
                break
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "cat-poet-" not in href:
                    continue
                full = href if href.startswith("http") else BASE_URL + "/" + href.lstrip("/")
                if full not in links:
                    links.append(full)
            cursor = data.get("next_cursor")
            if not cursor:
                break
            time.sleep(0.6)
        except Exception as e:
            print(f"  Error: {e}")
            break
    return links


def get_links_subcats_feed(cat_id):
    links, cursor = [], None
    feed = f"{BASE_URL}/cat-{cat_id}/subcats-feed"
    while True:
        url = f"{feed}?cursor={cursor}" if cursor else feed
        try:
            r = requests.get(url, headers=headers_api, timeout=15)
            data = r.json()
            html = data.get("html", "")
            if not html:
                break
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "cat-poet-" not in href:
                    continue
                full = href if href.startswith("http") else BASE_URL + "/" + href.lstrip("/")
                if full not in links:
                    links.append(full)
            cursor = data.get("next_cursor")
            if not cursor:
                break
            time.sleep(0.6)
        except Exception as e:
            print(f"  Error: {e}")
            break
    return links


def get_links_html(url):
    links = []
    try:
        r = requests.get(url, headers=headers_html, timeout=15)
        if r.status_code != 200:
            return links
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if "cat-poet-" not in href:
                continue
            full = href if href.startswith("http") else BASE_URL + "/" + href.lstrip("/")
            if full not in links:
                links.append(full)
    except Exception as e:
        print(f"  Error: {e}")
    return links


all_slugs = {}
all_links = {}

def add_links(links, country=None, era=None):
    added = 0
    for url in links:
        slug = url.split("cat-poet-")[-1].rstrip("/") if "cat-poet-" in url else None
        if not slug:
            continue
        if slug not in all_slugs:
            all_slugs[slug] = {"country": country, "era": era}
            all_links[slug] = url
            added += 1
        else:
            if country and not all_slugs[slug]["country"]:
                all_slugs[slug]["country"] = country
            if era and not all_slugs[slug]["era"]:
                all_slugs[slug]["era"] = era
    return added


def scrape_poet(url, country=None, era=None):
    r = requests.get(url, headers=headers_html, timeout=15)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    name = None
    h2 = soup.find("h2")
    if h2:
        name = h2.get_text(strip=True)

    if not country:
        c = soup.find("a", href=re.compile(r"/cat-poets-[a-zA-Z]"))
        if c:
            country = c.get_text(strip=True)

    biography = None
    h4 = soup.find("h4")
    if h4:
        biography = h4.get_text(" ", strip=True)

    poems_count = None
    m = re.search(r'(\d+)\s*قصيدة', text)
    if m:
        poems_count = int(m.group(1))

    birth_year = death_year = None
    if biography:
        years = re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", biography)
        if len(years) >= 1:
            birth_year = int(years[0])
        if len(years) >= 2:
            death_year = int(years[1])

    poet_id = None
    m2 = re.search(r"cat-(\d+)/poems-feed", r.text)
    if m2:
        poet_id = int(m2.group(1))

    slug = url.split("cat-poet-")[-1].rstrip("/") if "cat-poet-" in url else None

    return {
        "poet_id"    : poet_id,
        "name"       : name,
        "birth_year" : birth_year,
        "death_year" : death_year,
        "country"    : country,
        "era"        : era,
        "biography"  : biography,
        "poems_count": poems_count,
        "slug"       : slug,
        "source_url" : url,
    }


# source 1: authers-feed
for t in ["male", "female", "all"]:
    print(f"authers-feed type={t}")
    links = get_links_authers_feed(t)
    added = add_links(links)
    print(f"  {len(links)} found, {added} new. Total: {len(all_slugs)}")

# source 2: eras
for era_name, cat_id in ERAS.items():
    print(era_name)
    links = get_links_subcats_feed(cat_id)
    added = add_links(links, era=era_name)
    print(f"  {len(links)} found, {added} new. Total: {len(all_slugs)}")

# source 3: small countries
for country, url in SIMPLE_COUNTRIES.items():
    print(country)
    links = get_links_html(url)
    added = add_links(links, country=country, era="العصر الحديث")
    print(f"  {len(links)} found, {added} new. Total: {len(all_slugs)}")

# source 4: large countries
for country, cat_id in API_COUNTRIES.items():
    print(country)
    links = get_links_subcats_feed(cat_id)
    added = add_links(links, country=country, era="العصر الحديث")
    print(f"  {len(links)} found, {added} new. Total: {len(all_slugs)}")

print(f"\nTotal unique poets: {len(all_slugs)}")
print("Scraping profiles...")

poets = []
total = len(all_links)

for i, (slug, url) in enumerate(all_links.items(), 1):
    meta = all_slugs[slug]
    print(f"[{i}/{total}] {url}")
    try:
        poet = scrape_poet(url, country=meta["country"], era=meta["era"])
        poets.append(poet)
        time.sleep(0.5)
    except Exception as e:
        print(f"Error: {e}")

df = pd.DataFrame(poets)
df.to_csv("final_poets.csv", index=False, encoding="utf-8-sig")
print(f"Saved {len(poets)} poets to final_poets.csv")


# clean name column and extract country/era
def parse_name_column(value):
    value = str(value)
    parts = [p.strip() for p in value.split("»")]
    name   = parts[-1] if len(parts) >= 1 else ""
    middle = parts[1]  if len(parts) >= 3 else ""
    era_keywords = ["العصر", "المخضرمون"]
    is_era = any(kw in middle for kw in era_keywords)
    extracted_era     = middle if is_era else ""
    extracted_country = middle if not is_era else ""
    return name, extracted_country, extracted_era

results = df["name"].apply(parse_name_column)
df["name"] = results.apply(lambda x: x[0])

df["country"] = df.apply(
    lambda row: results[row.name][1] if pd.isna(row["country"]) or str(row["country"]).strip() == "" else row["country"],
    axis=1
)
df["era"] = df.apply(
    lambda row: results[row.name][2] if pd.isna(row["era"]) or str(row["era"]).strip() == "" else row["era"],
    axis=1
)

# set era to العصر الحديث for poets with country but no era
df.loc[
    df["country"].notna() & (df["country"].str.strip() != "") &
    (df["era"].isna() | (df["era"].str.strip() == "")),
    "era"
] = "العصر الحديث"

# drop empty rows and fill missing IDs
df = df[~(df["name"].isna() & df["slug"].isna())].reset_index(drop=True)

max_id = int(df["poet_id"].dropna().max())
for i, row in df.iterrows():
    if pd.isna(row["poet_id"]):
        max_id += 1
        df.at[i, "poet_id"] = max_id

df["poet_id"] = df["poet_id"].astype(int)
df = df.sort_values("poet_id", ascending=True).reset_index(drop=True)

df.to_csv("final_poets.csv", index=False, encoding="utf-8-sig")
print(f"Done. {len(df)} poets saved to final_poets.csv")
