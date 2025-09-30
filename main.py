from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

SYMBOL = "ETFBS80TR"
HEADLESS = True
WAIT_TIMEOUT = 8
MAX_PAGES = 10
OUTPUT_CSV = f"{SYMBOL}_history.csv"

def start_driver(headless=True):
    options = webdriver.FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    return webdriver.Firefox(options=options)

def accept_cookies_if_present(driver):
    try:
        button = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Zgadzam')]"))
        )
        button.click()
    except Exception:
        pass

def get_table_rows(driver):
    try:
        table = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        rows = []
        for row in table.find_elements(By.TAG_NAME, "tr"):
            cells = row.find_elements(By.XPATH, ".//th|.//td")
            rows.append([c.text.strip() for c in cells])
        return rows
    except Exception:
        return []

def scrape_all_pages(symbol, headless=True, max_pages=MAX_PAGES):
    driver = start_driver(headless)
    rows = []
    headers = None
    empty_count = 0

    try:
        for page in range(1, max_pages + 1):
            if page == 1:
                url = f"https://www.biznesradar.pl/notowania-historyczne/{symbol}"
            else:
                url = f"https://www.biznesradar.pl/notowania-historyczne/{symbol},{page}"

            driver.get(url)
            accept_cookies_if_present(driver)

            parsed = get_table_rows(driver)

            if not parsed:
                empty_count += 1
                if empty_count >= 3:
                    print("Error: empty pages")
                    break
                continue

            empty_count = 0

            if headers is None:
                headers = parsed[0]
                data = parsed[1:]
            else:
                data = parsed

            for row in data:
                if any(row):
                    rows.append(row)

    finally:
        driver.quit()

    if not rows:
        print("Error: no data")
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=headers[:len(rows[0])])

    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], format="%d.%m.%Y", errors="coerce")
        df = df.dropna(subset=["Data"])

    for col in ["Wolumen", "Obrót"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].str.replace(" ", ""), errors="coerce").astype("Int64")

    if df.empty:
        print("Error: cleaned empty")
    else:
        df.to_csv(OUTPUT_CSV, index=False)

    return df

if __name__ == "__main__":
    df = scrape_all_pages(SYMBOL, headless=HEADLESS, max_pages=MAX_PAGES)
    if df.empty:
        print("Error: final empty")
    else:
        print(df.head())
