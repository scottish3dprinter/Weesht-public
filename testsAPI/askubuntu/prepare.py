import csv
import json
from bs4 import BeautifulSoup
import html

def main():
    allTags = getTags()
    while missingTags := checkTagsInJson(allTags): 
        if missingTags:
            for tag in missingTags:
                print(tag)
            print(str(len(missingTags)) + " tags in file that are not in json")
            print("fix? Y/n")
            if input().strip().lower() == "n":
                return
            fixTags(missingTags)
    print("All tags are in the JSON")
    print("Do you want to make or replace the testing file? y/N")
    if input().strip().lower() != "y":
       return 
    makePreparedFile()
    
def makePreparedFile():
    with open("./testsAPI/askubuntu/TagCategory.json") as file:
        categoryMapping = json.load(file)
    with open("./testsAPI/askubuntu/QueryResults.csv") as oldFile:
        with open("./testsAPI/askubuntu/tickets.csv", "w") as newFile:
            reader = csv.reader(oldFile)
            next(reader, None)  #Skip the first row as it is the header row 
            #number, Title, Description, category, priority, resolver_team, Where I got the ticket from, hardness
            #These headers are to match what I have in the self made tickets
            headers = [
                "number",
                "Title",
                "Description",
                "category",
                "priority",
                "resolver_team",
                "Where I got the ticket from",
                "hardness"
            ]
            writer = csv.writer(newFile)
            writer.writerow(headers)

            for x, row in enumerate(reader, start=1):
                if len(row) > 2:
                    tags = str(row[2]).strip("<>").split("><")
                    expected = bestTag(tags, categoryMapping, row)
                    descriptionHtml = html.unescape(row[3])
                    descriptionText = BeautifulSoup(descriptionHtml, "html.parser").get_text(separator="\n", strip=True)
                    writer.writerow([x, row[1], descriptionText, expected, "", categoryToResolverTeam(expected), "askubuntu", ""])
                    
def categoryToResolverTeam(category):
    mapping = {
        "networking": "network support",
        "user accounts": "system support",
        "package management": "system support",
        "hardware": "hardware support",
        "installation": "installation support",
        "system settings": "desktop support",
        "system performance": "system support",
        "general usage": "general support"
    }
    return mapping[category]

def bestTag(tags, categoryMapping, row):
    ticketId = str(row[0].strip())
    with open("./testsAPI/askubuntu/TicketCategories.json") as file:
        ticketCategories = json.load(file)
    if ticketId in ticketCategories:
        return ticketCategories[ticketId]
    matchedCategories = []
    uniqueCategories = []
    for tag in tags:
        tag = tag.strip()
    
        if not tag:
            continue
        
        for category, categoryTags in categoryMapping.items():
            if tag in categoryTags:
                matchedCategories.append(category)
#    This IF was redundent after all tags were in TagCategory.json
#    if not matchedCategories:
#        print(str(tags) + " not in mapping. Using \"general usage\". Press enter to continue")
#        input()
#        return "general usage"

    #if there is only one category use that
    for category in matchedCategories:
        if category not in uniqueCategories:
            uniqueCategories.append(category)
    if len(uniqueCategories) == 1:
        writeToTicketCategories(ticketId, str(matchedCategories[0]), ticketCategories)
        return str(matchedCategories[0])
    
    #If there is one category that is in matchedCategories a lot more than others use that  
    categoryCounts = {}
    for category in uniqueCategories:
        categoryCounts[category] = matchedCategories.count(category)
    highestCount = max(categoryCounts.values())

    highestCategories = []
    for category, count in categoryCounts.items():
        if count == highestCount:
            highestCategories.append(category)

    if len(highestCategories) == 1:
        writeToTicketCategories(ticketId, highestCategories[0], ticketCategories)
        return highestCategories[0]

    #Manualy ask the user for input
    print("\n\n\n\nTicket ID: " + str(row[0]))
    print("Title: " + str(row[1]))
    print("Tags: " + str(tags))
    print("To put tags into categories type the number you want to add it too")
    for x, category in enumerate(highestCategories, start=1):
        print(str(x) + ". " + str(category) + ": " + str(matchedCategories.count(category)))
    while True:
        choice = input("choice: ")
        if not choice.isdigit():
            print("Input must be numeric")
            continue
        choiceNumber = int(choice)

        if 1 <= choiceNumber <= len(highestCategories):
            writeToTicketCategories(ticketId, str(highestCategories[choiceNumber - 1]), ticketCategories)
            return str(highestCategories[choiceNumber - 1])
        
        print("invaild input")

def writeToTicketCategories(ticketId, category, ticketCategories):
    with open("./testsAPI/askubuntu/TicketCategories.json", "w") as file:
        ticketCategories[ticketId] = category
        json.dump(ticketCategories, file, indent=4, sort_keys=True)

def fixTags(missingTags):
    print("To put tags into categories type the number you want to add it too")
    with open("./testsAPI/askubuntu/TagCategory.json") as file:
        categoryMapping = json.load(file)
    categories = list(categoryMapping.keys())
    for tag in sorted(missingTags):
        print("\n\n\n\nTag: " + str(tag))
        print("Blank input is \"general usage\"")
        print("0. save and exit")
        for index, category in enumerate(categories, start=1):
            print(str(index) + ". " + str(category))
        while True:
            choice = input("choice: ")
            if choice == "":
                categoryMapping["general usage"].append(tag)
                break
            if not choice.isdigit():
                print("Input must be numeric")
                continue
            choiceNumber = int(choice)
            if choiceNumber == 0:
                saveMapping(categoryMapping)
                return

            if 1 <= choiceNumber <= len(categories):
                selectedCategory = categories[choiceNumber - 1]
                categoryMapping[selectedCategory].append(tag)
                break
            print("invaild input")
    saveMapping(categoryMapping)


def saveMapping(category_mapping):
    with open("./testsAPI/askubuntu/TagCategory.json", "w") as file:
        json.dump(category_mapping, file, indent=4)


def checkTagsInJson(tags):
    tagsInJson = set()
    with open("./testsAPI/askubuntu/TagCategory.json") as file:
        reader = json.load(file)

    for category, categoryTags in reader.items():
        print("category: " + str(category))
        print("categoryTags: " + str(categoryTags))
        for tag in categoryTags:
            if tag in tagsInJson:
                raise ValueError("A tags can not map to the diffrent master tags \"" + str(tag) + "\" is in the JSON more than once please manually fix and run again")
            tagsInJson.add(tag)
    return tags - tagsInJson

def getTags():
    tags = set()

    with open("./testsAPI/askubuntu/QueryResults.csv", newline="") as file:
        reader = csv.reader(file)
        next(reader, None)  #Skip the first row as it is the header row 
        for row in reader:
            if len(row) > 2:
                for tag in str(row[2]).strip("<>").split("><"):
                    tags.add(tag)
    return tags

if __name__ == "__main__":
    main()