import requests

robot_url = "https://books.toscrape.com/robots.txt"

def main():
    response = requests.get(robot_url,timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 404 : 
        print("no robots file found")

if __name__ == "__main__":
    main()