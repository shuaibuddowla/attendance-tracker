import urllib.request
import urllib.parse
import re
import os

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Download dialog POST
update_ids = ['34213758-173c-47ec-951d-16b2c9463881', 'a355a6f6-2557-44be-90c6-c9940c900de6']
for uid in update_ids:
    post_data = urllib.parse.urlencode({'updateIDs': f'[{{\"size\":0,\"languages\":\"\",\"uidInfo\":\"{uid}\",\"updateID\":\"{uid}\"}}]'}).encode('utf-8')
    req = urllib.request.Request('https://www.catalog.update.microsoft.com/DownloadDialog.aspx', data=post_data, headers=headers)
    resp = urllib.request.urlopen(req).read().decode('utf-8')
    links = re.findall(r'downloadInformation\[\d+\]\.files\[\d+\]\.url\s*=\s*[\'\"]([^\'\"]+)[\'\"]', resp)
    print(f'Update {uid} links:', links)
    if links:
        cab_url = links[0]
        print(f"Downloading {cab_url}...")
        cab_dest = os.path.join(os.path.dirname(__file__), "cp210x_driver.cab")
        urllib.request.urlretrieve(cab_url, cab_dest)
        print(f"Downloaded: {os.path.getsize(cab_dest)} bytes to {cab_dest}")
        break
