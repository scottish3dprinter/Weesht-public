from openai import OpenAI
import csv
import json
from pathlib import Path

client = OpenAI()

def openAIapicall(title, description):
    response = client.responses.create(
        model="gpt-5-mini",
        input=f"""
    You are a help desk ticket triage assistant.

    Your job is to classify the following support ticket into:
    1. Category
    2. Priority
    3. Resolver team
    4. Short reason

    You must choose only from the allowed values below.

    Allowed categories:
    - networking
    - user accounts
    - package management
    - hardware
    - installation
    - system settings
    - system performance
    - general usage

    Allowed priorities:
    - 1
    - 2
    - 3
    - 4

    Priority meaning:
    - 1 = Critical: system unusable or user cannot access system
    - 2 = High: major feature unavailable but system still usable
    - 3 = Medium: limited issue or non-urgent support request
    - 4 = Low: minor issue, advice, or information request

    Allowed resolver teams:
    - network support
    - system support
    - desktop support
    - hardware support
    - installation support
    - general support

    Return your answer in exactly this JSON format:
    {{
    "category": "one allowed category",
    "priority": 1,
    "resolver_team": "one allowed resolver team",
    "reason": "short explanation"
    }}

    Always respond with the JSON object it is not possible to ask for more information from the user.
    Never use commas in the reason field. If you need to separate multiple points in the reason, use semicolons or periods instead.

    If which category the ticket belongs to is not clear from the title and description, choose the most likely category do not return "unclear" or "unknown". If the priority is not clear, choose the lowest priority (4). If the resolver team is not clear, choose the most likely resolver team do not return "unclear" or "unknown".

    Ticket:
    - Title: {title}
    - Description: {description}
    """    
    )

    return json.loads(response.output_text)

def csvTestAPI(limit=None):
    results = []

    #get input from user for Paths
    while True:
        inPath = Path(input("in path ")) #   "./testsAPI/SelfMadeTickets/tickets.csv" "./testsAPI/askubuntu/tickets.csv"
        outPath = Path(input("out path ")) # "./testsAPI/SelfMadeTickets/results.csv" "./testsAPI/askubuntu/results.csv"
        if not inPath.is_file:
            print("in path must be a file")
            continue
        if inPath.suffix.lower() != ".csv":
            print("in path must be a CSV file")
            continue
        break
    with open(inPath, newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) < 6:
                continue
            if row[1].strip().lower() == "title":
                continue
            if limit is not None and len(results) >= limit:
                break
            if limit is not None:
                print(str(len(results) + 1) + "/" + str(limit) )
            print(row[1].strip(), row[2].strip())
            result = (row[1].strip(), row[2].strip(), openAIapicall(row[1].strip(), row[2].strip()), row[3].strip(), row[4].strip(), row[5].strip())
            results.append(result)

    with open(outPath, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["title", "description", "expected category", "expected priority", "expected resolver_team", "actual category", "actual priority", "actual resolver_team", "reason", "category same T/F", "resolver same T/F"])
        for result in results:
            writer.writerow([result[0] , result[1], result[3], result[4], result[5], result[2]["category"], result[2]["priority"], result[2]["resolver_team"], result[2]["reason"].replace(',', ';'),  str(result[3].strip()).strip().lower() == str(result[2]["category"].strip()).strip().lower(),  str(result[5].strip()).strip().lower() == str(result[2]["resolver_team"].strip()).strip().lower()])
if __name__  == "__main__":
    csvTestAPI()