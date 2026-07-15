I got the data from https://data.stackexchange.com/askubuntu

I used this sql so I did not need to download the full database
'''sql
SELECT TOP 500
    Id,
    Title,
    Tags,
    Body
FROM Posts
WHERE PostTypeId = 1
ORDER BY Score DESC
'''
I then downloaded the much smaller CSV

I used the prepare.py to make tickets.csv from this

In doing so it also made 2 json files that would make it quicker if I was to add more than 500 rows. The json saves all the manual choices so the script can be consistent and quicker.