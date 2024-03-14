import requests

class cbc_connection(object):
    def __init__(self, uuid, prod, api_id, api_sec, org_key, org_id):
        self.uuid = uuid
        self.api_id = api_id
        self.api_sec = api_sec
        self.org_key = org_key
        self.org_id = org_id
        self.prod = prod
        if self.uuid:
            self.session = self.get_session()

    def get_api_details(self):
        ''' With api creds, return the backend, org_key, and org_id'''
        backends = {
            "prod05":"https://defense-prod05.conferdeploy.net",
            "prod02":"https://defense.conferdeploy.net",
            "prod06":"https://defense-eu.conferdeploy.net",
            "prod01":"https://dashboard.confer.net",
            "prodnrt":"https://defense-prodnrt.conferdeploy.net",
            "prodsyd":"https://defense-prodsyd.conferdeploy.net",
            "produk": "https://ew2.carbonblackcloud.vmware.com",
            "govcloud": "https://gprd1usgw1.carbonblack-us-gov.vmware.com"
        }
        headers = {
            "X-Auth-Token": "{}/{}".format(self.api_sec, self.api_id),
            "Content-Type": "application/json"
            }
        for prod in backends:
            backend = backends[prod]
            url = "/appservices/v5/delegations"
            r = requests.get(backend + url, headers=headers)
            if r.status_code == 200 and r.json()["numHits"] > 0:
                # Mssp setups can have multiple orgs in the delegation call
                # the following calls the entitlements api with the various org_keys
                # until we get to the one that returns a 200; the correct one to use
                orgs = [i for i in r.json()["organizations"]]
                for org in orgs:
                    org_key = org["orgKey"]
                    url = f"/entitlements/v1/orgs/{org_key}/details"
                    working = requests.get(backend + url, headers=headers)
                    if working.status_code == 200:
                        org_key = org["orgKey"]
                        org_id = org["id"]
                        name = org["name"]
                        break
                return backends[prod], org_key, org_id, name
        return False

    def get_session(self):
        headers = {
            "X-Auth-Token": "{}/{}".format(self.api_sec, self.api_id),
            "accept": "application/json"
        }
        session = requests.Session()
        session.headers = headers
        return session

    def get_req(self, url):
        data = self.session.get(f"{self.prod}{url}")
        if data.status_code == 200:
            return data.json()

    def single_post(self, url, data, count_only=False):
        print (f"POST {url}")
        url = f"{self.prod}{url}"
        r = self.session.post(url, json=data)
        if r.status_code == 200:
            r = r.json()
            if "num_found" in r or "numHits" in r:
                hits = r["num_found"] if "num_found" in r else r["numHits"]
            if count_only:
                response_data = hits
            else:
                response_data = r["results"] if "results" in r else r["entries"]
        else:
            response_data = False
        return response_data

    def post_req(self, url, data, max_rows=True, count_only=False):
        print (f"POST {url}")
        url = f"{self.prod}{url}"
        r = self.session.post(url, json=data)
        if r.status_code == 200:
            if not max_rows:
                return r.json()
            r = r.json()
            results = []
            max_rows = data["rows"] if "rows" in data else data["maxRows"]
            if "num_found" in r or "numHits" in r:
                hits = r["num_found"] if "num_found" in r else r["numHits"]
            else:
                return r
            if count_only:
                return hits
            if "devices" not in url:
                hits = 10000 if int(hits) > 10000 else hits
            else:
                hits = 100000 if int(hits) > 100000 else hits
            results = r["results"] if "results" in r else r["entries"]
            if hits > max_rows:
                pages = int(hits / max_rows)
                pages = pages + 1 if hits % max_rows != 0 else pages
                for x in range(1, pages):
                    if "start" in data:
                        data["start"] += max_rows
                    else:
                        data["fromRow"] += max_rows
                    r = self.session.post(url, json=data)
                    r = r.json()
                    try:
                        r = r["results"] if "results" in r else r["entries"]
                    except KeyError:
                        import json
                        print(json.dumps(r, indent=2))
                        print(json.dumps(data, indent=2))
                        raise
                    results.extend(r)
            return results
        elif r.status_code == 504:
            return False
        elif r.status_code > 299:
            with open("jbg_look_at_this.txt", "wb") as f:
                f.write(r.content)
            with open("jbg_look_at_this2.txt", "w") as f:
                f.write(f"{self.api_id} - {self.api_sec} - {self.org_id} - {self.org_key}")
            # to handle when watchlist alerts are not available
            if "message" in r.json():
                if "alerts are not available for your organization" in r.json()["message"]:
                    return "Not available"
                elif "User is not authenticated" in r.json()["message"]:
                    print(f"{self.api_id} is not working")
                    return False
            else:
                print(r.json())
                ben
        else:
            return False
