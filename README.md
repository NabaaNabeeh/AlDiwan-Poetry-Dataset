# AlDiwan-Poetry-Dataset-scraped

A structured dataset of Arabic poetry scraped from https://www.aldiwan.net, one of the largest Arabic poetry websites. The dataset covers poets and poems spanning from different literary eras.

---

## Dataset Overview

| Dataset | Rows | Description |
|---|---|---|
| `final_poets.csv` | ~2,561 | One row per poet |
| `final_poems.csv` | ~128,499 | One row per poem |

---

## Poets Dataset (`final_poets.csv`)

| Column | Description |
|---|---|
| `poet_id` | Unique poet identifier |
| `name` | Poet's name in Arabic |
| `birth_year` | Year of birth |
| `death_year` | Year of death |
| `country` | Poet's country |
| `era` | Literary era (e.g. العصر الجاهلي, العصر الحديث) |
| `biography` | Short biography in Arabic |
| `poems_count` | Number of poems on the site |
| `slug` | URL slug used as a unique key |
| `source_url` | Poet's profile URL |

---

## Poems Dataset ( [Arabic Poetry Dataset](https://huggingface.co/datasets/Fatimah8Moheeb/Arabic-Poetry-Dataset/blob/main/full_final_poems.csv) )


| Column | Description |
|---|---|
| `poem_id` | Unique poem identifier |
| `poet_id` | Foreign key linking to poets dataset |
| `title` | Poem title in Arabic |
| `full_text` | Complete poem text |
| `poet_name` | Poet's name |
| `era` | Literary era |
| `theme` | Poem theme/topic |
| `verses_count` | Number of verses |
| `source_url` | Poem's URL |

---

## Team Members

- Nabaa Alaswad
- Fatimah Alwarsh

---

## Source

All data was collected from https://www.aldiwan.net for academic and research purposes.

---

## Tools Used

- Python 3
- `requests` — HTTP requests
- `BeautifulSoup` — HTML parsing
- `pandas` — Data processing
