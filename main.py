import requests
import time
from typing import List, Dict
import json

class SolanaWalletChecker:
    def __init__(self, min_balance_usd: float = 50.0):
        self.min_balance_usd = min_balance_usd
        self.rpc_url = "https://api.mainnet-beta.solana.com"
        self.sol_price_usd = self.get_sol_price()
        
    def get_sol_price(self) -> float:
        try:
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "solana", "vs_currencies": "usd"},
                timeout=10
            )
            return response.json()["solana"]["usd"]
        except Exception as e:
            print(f"⚠️  Ошибка получения цены SOL: {e}")
            return 150.0
    
    def get_wallet_balance(self, address: str) -> Dict:
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [address]
            }
            
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            data = response.json()
            
            if "error" in data:
                return {"valid": False, "error": data["error"]}
            
            balance_lamports = data["result"]["value"]
            balance_sol = balance_lamports / 1_000_000_000
            balance_usd = balance_sol * self.sol_price_usd
            
            token_balance_usd = self.get_token_accounts(address)
            total_usd = balance_usd + token_balance_usd
            
            return {
                "valid": True,
                "address": address,
                "sol_balance": balance_sol,
                "sol_usd": balance_usd,
                "tokens_usd": token_balance_usd,
                "total_usd": total_usd,
                "meets_minimum": total_usd >= self.min_balance_usd
            }
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def get_token_accounts(self, address: str) -> float:
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    address,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                    {"encoding": "jsonParsed"}
                ]
            }
            
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            data = response.json()
            
            if "error" in data or "result" not in data:
                return 0.0
            
            total_usd = 0.0
            accounts = data["result"]["value"]
            
            for account in accounts[:10]:
                try:
                    token_amount = float(
                        account["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]
                    )
                    if token_amount > 0:
                        total_usd += token_amount * 0.1
                except:
                    continue
            
            return total_usd
            
        except Exception as e:
            return 0.0
    
    def check_addresses_from_file(self, filename: str, output_file: str = "valid_wallets.txt"):
        print(f"🚀 Запуск проверки кошельков Solana")
        print(f"💵 Минимальный баланс: ${self.min_balance_usd}")
        print(f"💰 Текущая цена SOL: ${self.sol_price_usd:.2f}")
        print("-" * 60)
        
        try:
            with open(filename, 'r') as f:
                addresses = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"❌ Файл {filename} не найден!")
            return
        
        valid_wallets = []
        total_checked = 0
        
        for i, address in enumerate(addresses, 1):
            print(f"\n[{i}/{len(addresses)}] Проверка: {address[:8]}...{address[-8:]}")
            
            result = self.get_wallet_balance(address)
            total_checked += 1
            
            if not result["valid"]:
                print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
                continue
            
            if result["meets_minimum"]:
                print(f"✅ НАЙДЕН! Баланс: ${result['total_usd']:.2f}")
                print(f"   SOL: {result['sol_balance']:.4f} (${result['sol_usd']:.2f})")
                print(f"   Токены: ~${result['tokens_usd']:.2f}")
                valid_wallets.append(result)
            else:
                print(f"⏭️  Пропущен. Баланс: ${result['total_usd']:.2f}")
            
            time.sleep(0.5)
        
        if valid_wallets:
            with open(output_file, 'w') as f:
                for wallet in valid_wallets:
                    f.write(f"{wallet['address']}\n")
                    f.write(f"  Total: ${wallet['total_usd']:.2f}\n")
                    f.write(f"  SOL: {wallet['sol_balance']:.4f}\n")
                    f.write("-" * 50 + "\n")
        
        print("\n" + "=" * 60)
        print(f"📊 ИТОГИ:")
        print(f"   Проверено адресов: {total_checked}")
        print(f"   Найдено валидных: {len(valid_wallets)}")
        if valid_wallets:
            total_value = sum(w['total_usd'] for w in valid_wallets)
            print(f"   Общая стоимость: ${total_value:.2f}")
            print(f"   Результаты сохранены в: {output_file}")
        print("=" * 60)


def main():
    input_file = "addresses.txt"
    min_balance = 50.0
    
    checker = SolanaWalletChecker(min_balance_usd=min_balance)
    checker.check_addresses_from_file(input_file)


if __name__ == "__main__":
    main()
