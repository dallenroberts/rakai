import json

with open('config_rakai.json') as f:
    json_data = json.load(f)

with open('config_rakai_sorted.json', 'w') as f:
    json_str = json.dumps(json_data, indent = 4, sort_keys = True) 
    f.write(json_str)