# cli.py
import requests
import json

API_URL = "http://127.0.0.1:5000/task"

def post(action, query=None):
    payload = {"action": action}
    if query:
        payload["q"] = query
    try:
        res = requests.post(API_URL, json=payload)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print("❌ Error:", e)
        return {}

def show_results(data):
    results = data.get("results", [])
    if not results:
        print("❌ No matching files found.")
        return
    print("\n🔍 Top Matches:")
    for i, r in enumerate(results, 1):
        print(f"{i}. 📄 {r['filename']}")
        print(f"   📁 Path: {r['path']}")
        print(f"   🕒 Modified: {r.get('modified', 'Unknown')}")
        print(f"   📦 Type: {r['extension']}\n")

def main():
    while True:
        print("\n📚 Document Finder CLI")
        print("1. Accept Terms & Full Scan")
        print("2. Smart Rescan")
        print("3. Search")
        print("4. Check Status")
        print("5. Exit")
        choice = input("👉 Choose (1-5): ").strip()

        if choice == "1":
            res = post("accept")
            print("✅", res.get("message", ""))
        elif choice == "2":
            res = post("smart-rescan")
            print("✅", res.get("message", ""))
        elif choice == "3":
            q = input("🔎 Enter search query: ").strip()
            res = post("search", query=q)
            show_results(res)
        elif choice == "4":
            res = post("status")
            print(json.dumps(res, indent=2))
        elif choice == "5":
            print("👋 Exiting CLI.")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()