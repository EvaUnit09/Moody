from collections import defaultdict

strs = ["cat", "bat", "act", "tab"]

map = defaultdict(list)

for word in strs:
    sortedW = "".join(sorted(word))
    map[sortedW].append(word)

print(list(map.values()))



    
