from selenium import webdriver
import pandas as pd
import time

# 🔧 konfiguracja
BASE_URL = "https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/mazowieckie/warszawa/warszawa/warszawa"

driver = webdriver.Chrome()

all_results = []

page = 1

while True and page <6:
    url = f"{BASE_URL}?page={page}"
    print(f"➡️ Strona {page}")

    driver.get(url)
    time.sleep(5)

    # 🔥 pobieramy JSON z Next.js
    data = driver.execute_script("return window.__NEXT_DATA__")

    try:
        offers = data["props"]["pageProps"]["data"]["searchAds"]["items"]
    except KeyError:
        print("❌ Zmieniła się struktura strony")
        break

    # jeśli brak ofert → koniec
    if not offers:
        print("✅ Koniec wyników")
        break

    print(f"   Znaleziono: {len(offers)} ofert")

    for offer in offers:
        price_data = offer.get("totalPrice") or {}
        location_data = offer.get("location") or {}
        address_data = location_data.get("address") or {}

        all_results.append({
            "title": offer.get("title"),
            "price": price_data.get("value"),
            "currency": price_data.get("currency"),
            "area_m2": offer.get("areaInSquareMeters"),
            "rooms": offer.get("roomsNumber"),
            "district": address_data.get("district"),
        })

    page += 1
    time.sleep(2)  # żeby nie wyglądać jak bot

driver.quit()

# 📊 DataFrame
df = pd.DataFrame(all_results)

# 🧠 dodatkowe pole
df["price_per_m2"] = df["price"] / df["area_m2"]

print(df.head())
print(f"\n📊 Łącznie ofert: {len(df)}")

# 💾 zapis
df.to_csv("otodom_warszawa.csv", index=False)

print("💾 Zapisano do otodom_warszawa.csv")