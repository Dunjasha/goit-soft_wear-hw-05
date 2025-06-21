import asyncio
import aiohttp
from datetime import datetime, timedelta
import sys
import json


class PrivatBankAPI:
    BASE_URL = "https://api.privatbank.ua/p24api/exchange_rates?json&date="

    async def fetch_rates_for_date(self, session: aiohttp.ClientSession, date: datetime) -> dict:
        url = self.BASE_URL + date.strftime("%d.%m.%Y")
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP error {response.status} for date {date.strftime("%Y-%m-%d")}")
                data = await response.json()
                return data
        except aiohttp.ClientError as e:
            raise Exception(f"Network error when fetching data for {date.strftime("%Y-%m-%d")}: {e}")
        except Exception as e:
            raise Exception(f"Error fetching data for {date.strftime("%Y-%m-%d")}: {e}")
        
class ExchangeRateService:
    def __init__(self, api: PrivatBankAPI):
        self.api = api

    async def get_rates_for_days(self, days: int):
        if days > 10 or days < 1:
            raise ValueError("Кількість днів має бути від 1 до 10")
    
        async with aiohttp.ClientSession() as session:
            results = []
            for day_delta in range(days):
                date = datetime.today() - timedelta(days=day_delta)
                try:
                    data = await self.api.fetch_rates_for_date(session, date)
                    rates = self.extract_usd_eur(data)
                    results.append((date.strftime("%Y-%m-%d"), rates))
                except Exception as e:
                    print(f"Помилка: {e}", file=sys.stderr)
            return results

    def extract_usd_eur(self, data: dict):
        rates = {}
        try:
            exchange_rates = data.get("exchangeRate", [])
            for item in exchange_rates:
                currency = item.get("currency")
                if currency in ("USD", "EUR"):
                    rates[currency] = {
                        "purchaseRate": item.get("purchaseRate", None),
                        "saleRate": item.get("saleRate", None)
                    }
        except Exception as e:
            raise Exception(f"Помилка обробки даних API: {e}")
        return rates   
    
class ConsoleApp:
    def __init__(self, service: ExchangeRateService):
        self.service = service

    async def run(self):
        try:
            days = int(input("Введіть кількість днів (макс 10): "))
            results = await self.service.get_rates_for_days(days)
            
            output_data = []
            for date_str, rates in results:
                day_entry = {
                    date_str: {
                        ccy: {
                            "purchase": rates[ccy]["purchaseRate"],
                            "sale": rates[ccy]["saleRate"]
                        } for ccy in rates
                    }
                }
                output_data.append(day_entry)

            with open("exchange_rates.json", "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            print(f"\nДані збережено у файлі exchange_rates.json")

        except ValueError as e:
            print(f"Невірне введення: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Виникла помилка: {e}", file=sys.stderr)


if __name__ == "__main__":
    import platform
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    api = PrivatBankAPI()
    service = ExchangeRateService(api)
    app = ConsoleApp(service)

    asyncio.run(app.run())
