from requests import Session, Request

def parse_http_bytes(http_bytes):
    top_and_header_end_index = http_bytes.index(b"\r\n\r\n")
    top_and_header = http_bytes[:top_and_header_end_index]
    body = http_bytes[top_and_header_end_index+4:]
    headers = top_and_header.split(b'\r\n')
    top = headers[0]
    headers = headers[1:]
    
    top = [i for i in top.decode().split()]
    headers = [i.decode().split(": ") for i in headers]
    headers = {i[0]: ": ".join(i[1:]) for i in headers}
    return top, headers, body

def make_request(http_bytes):
    top, headers, body = parse_http_bytes(http_bytes)
    s = Session()
    req = Request(top[0],top[1],data=body,headers=headers)
    req = req.prepare()
    resp = s.send(req)
    s.close()
    return resp.status_code, resp.headers, resp.content

def make_request_from_file(file):
    with open(file,"rb") as f:
        raw_req = f.read()
    return make_request(raw_req)