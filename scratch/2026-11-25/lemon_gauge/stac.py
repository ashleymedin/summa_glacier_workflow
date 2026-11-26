import json,urllib.request
b={"collections":["sentinel-2-l2a"],"bbox":[-134.40,58.395,-134.355,58.42],"limit":200,"query":{"eo:cloud_cover":{"lt":35}}}
out=[]
for y in range(2016,2027):
    b["datetime"]=f"{y}-07-20T00:00:00Z/{y}-10-05T00:00:00Z"
    r=urllib.request.Request("https://earth-search.aws.element84.com/v1/search",json.dumps(b).encode(),{"Content-Type":"application/json"})
    for f in json.load(urllib.request.urlopen(r,timeout=90))["features"]:
        out.append((f["properties"]["datetime"][:10],round(f["properties"]["eo:cloud_cover"]),f["assets"]["visual"]["href"] if "visual" in f["assets"] else None,f["id"]))
json.dump(sorted(out),open('stac.json','w'))
for o in sorted(out): print(o[0],o[1],o[3])
